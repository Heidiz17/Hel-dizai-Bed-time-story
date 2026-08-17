import os
import re
import asyncio
import sys
import time
import urllib.request
import edge_tts
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

TAG_AUDIO_MAP = {
    '[雷雨]': 'thunder.mp3',
    '[雷聲]': 'thunder.mp3',
    '[雨聲雷鳴]': 'thunder.mp3',
    '[風雨雷電]': 'thunder.mp3',
    '[下雨]': 'rain.mp3',
    '[雨聲]': 'rain.mp3',
    '[海洋]': 'wave.mp3',
    '[海浪]': 'wave.mp3',
    '[海浪風鈴]': 'wave.mp3',
    '[柴火]': 'fire.mp3',
    '[溫暖]': 'fire.mp3',
    '[森林]': 'forest.mp3',
    '[天地]': 'forest.mp3',
    '[森林鳥鳴]': 'forest.mp3',
    '[風鈴]': 'windbell.mp3',
    '[海鳥]': 'windbell.mp3',
    '[溪流]': 'stream.mp3',
    '[流水]': 'stream.mp3',
    '[戰爭]': 'war.mp3',
    '[交戰]': 'war.mp3',
    '[洞穴]': 'cave.mp3',
    '[水滴]': 'cave.mp3'
}

MUSIC_MAP = {
    'happy': 'music_happy.mp3',
    'sad': 'music_sad.mp3',
    'calm': 'music_calm.mp3'
}

VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',   # P仔
    'girl': 'zh-HK-HiuMaanNeural'   # P女
}

def download_chinese_font():
    """自動下載標準高清中文字型，解決豆腐塊及字體太小問題"""
    font_path = "CustomFont.ttf"
    if not os.path.exists(font_path):
        print("📥 正在為伺服器自動下載中文字型檔 (Noto Sans CJK)...")
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChineseHK/NotoSansCJKhk-Bold.otf"
        try:
            urllib.request.urlretrieve(font_url, font_path)
            print("✅ 字型下載完成！")
        except Exception as e:
            print(f"⚠️ 字型下載失敗，嘗試備用來源: {e}")
            alt_url = "https://raw.githubusercontent.com/everdrive/fceux/master_v2.2.3/output/fonts/wqy-zenhei.ttc"
            try:
                urllib.request.urlretrieve(alt_url, font_path)
            except Exception as ex:
                print(f"⚠️ 備用字型亦下載失敗: {ex}")
    return font_path if os.path.exists(font_path) else None

def create_title_cover(base_image_path, title_text, output_image_path):
    """喺封面圖正中間加上放大版招牌同章節標題"""
    try:
        font_file = download_chinese_font()
        
        img = Image.open(base_image_path).convert("RGBA")
        width, height = img.size
        
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        rect_top = int(height * 0.32)
        rect_bottom = int(height * 0.68)
        draw.rectangle([(0, rect_top), (width, rect_bottom)], fill=(0, 0, 0, 170))
        
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        brand_font_size = int(height * 0.08)
        title_font_size = int(height * 0.12)
        
        if font_file:
            brand_font = ImageFont.truetype(font_file, brand_font_size)
            title_font = ImageFont.truetype(font_file, title_font_size)
        else:
            brand_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            
        brand_text = "★ 廣東話聖經劇場 ★"
        
        draw.text((width / 2, height * 0.42), brand_text, font=brand_font, fill=(255, 215, 0), anchor="mm")
        draw.text((width / 2, height * 0.58), title_text, font=title_font, fill=(255, 255, 255), anchor="mm")
        
        img.save(output_image_path)
        print(f"🎨 已成功生成高清居中標題封面: {output_image_path}")
        return True
    except Exception as e:
        print(f"⚠️ 生成標題封面失敗: {e}")
        return False

async def generate_tts(text, voice, output_mp3):
    # ⚡ 支援 SSML 語音標籤轉換：將稿件入面嘅 <break time="xxx"/> 轉成 edge-tts 支援嘅格式
    # 先清除一般中括號標籤
    clean_ssml = re.sub(r'\[.*?\]', '', text)
    
    # 將 <break time="600ms"/> 或 <break time="1.5s"/> 轉化為 SSML 結構，讓微軟引擎識得停頓
    # 透過包裝成完整 SSML 格式發送給 edge_tts
    formatted_ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-HK">
        <voice name="{voice}">
            <prosody rate="-20%">
                {clean_ssml}
            </prosody>
        </voice>
    </speak>"""

    for attempt in range(8):
        try:
            # 透過 SSML 模式直接讓微軟引擎讀出停頓，並維持 -20% 黃金慢讀
            communicate = edge_tts.Communicate(formatted_ssml, voice)
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1000:
                print(f"✅ [{voice}] SSML 語音合成成功！")
                return True
        except Exception as e:
            print(f"⚠️ [{voice}] 重試第 {attempt+1} 次 (錯誤: {e})...")
            await asyncio.sleep(3)
    return False

def mix_chapter(text_file, gender, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    bg_music_type = 'calm'
    bgm_match = re.search(r'\[BGM\s*:\s*(happy|calm|sad)\]', raw_content, re.IGNORECASE)
    if bgm_match:
        bg_music_type = bgm_match.group(1).lower()

    print(f"🎵 偵測到背景音樂類型: {bg_music_type}")
    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    
    pattern = r'(\[.*?\])'
    parts = re.split(pattern, raw_content)
    
    sections = []
    current_tag = None
    
    for part in parts:
        if not part.strip():
            continue
        if re.match(r'\[BGM\s*:', part, re.IGNORECASE) or re.match(r'\[TITLE\s*:', part, re.IGNORECASE):
            continue
        if part in TAG_AUDIO_MAP or part.startswith('['):
            current_tag = part
        else:
            sections.append((current_tag, part.strip()))

    if not sections:
        sections = [(None, raw_content.strip())]

    combined_voice = AudioSegment.silent(duration=0)
    combined_sfx = AudioSegment.silent(duration=0)
    created_temp_files = []

    for idx, (tag, text) in enumerate(sections):
        temp_file = f"temp_{gender}_{idx}.mp3"
        created_temp_files.append(temp_file)
        success = asyncio.run(generate_tts(text, voice, temp_file))
        
        if not success or not os.path.exists(temp_file):
            continue

        raw_voice = AudioSegment.from_file(temp_file)
        seg_dur = len(raw_voice) + 1500
        
        a_file = TAG_AUDIO_MAP.get(tag, None)
        seg_sfx = AudioSegment.silent(duration=seg_dur)

        if a_file and os.path.exists(a_file):
            snd = AudioSegment.from_file(a_file)
            snd_looped = (snd * (int(seg_dur / len(snd)) + 1))[:seg_dur] - 22
            seg_sfx = snd_looped.fade_in(500).fade_out(1000)

        combined_voice += raw_voice + AudioSegment.silent(duration=1500)
        combined_sfx += seg_sfx

    for t_file in created_temp_files:
        if os.path.exists(t_file):
            os.remove(t_file)

    if len(combined_voice) == 0:
        print(f"❌ {gender} ({voice}) 語音生成失敗。")
        return

    total_dur = len(combined_voice) + 4000
    
    music_track = AudioSegment.silent(duration=total_dur)
    music_filename = MUSIC_MAP.get(bg_music_type, 'music_calm.mp3')
    
    if music_filename and os.path.exists(music_filename):
        print(f"🔊 正在混入背景音樂: {music_filename}")
        bg_music = AudioSegment.from_file(music_filename)
        
        target_loudness = -22.0
        change_in_dBFS = target_loudness - bg_music.dBFS
        bg_music = bg_music.apply_gain(change_in_dBFS)
        
        music_looped = (bg_music * (int(total_dur / len(bg_music)) + 1))[:total_dur]
        music_track = music_looped.fade_out(4000)
    else:
        print(f"⚠️ 找不到音樂檔: {music_filename}")

    final_mix = music_track.overlay(combined_sfx[:total_dur]).overlay(combined_voice, position=1000)
    final_mix.export(output_filename, format="mp3")
    print(f"🎉 臨時音訊混音完成: {output_filename}")

def generate_mp4(audio_file, video_output, text_file="input.txt"):
    try:
        from moviepy import AudioFileClip, ImageClip
        
        base_image = 'cover.png' if os.path.exists('cover.png') else 'default_cover.png'
        if not os.path.exists(base_image):
            print(f"⚠️ 找不到封面圖片 ({base_image})，跳過 MP4 合成。")
            return

        title_text = "創世記 第一章"
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                title_match = re.search(r'\[TITLE\s*:\s*(.*?)\]', content, re.IGNORECASE)
                if title_match:
                    title_text = title_match.group(1).strip()

        final_cover = "final_cover_with_title.png"
        create_title_cover(base_image, title_text, final_cover)
        
        used_image = final_cover if os.path.exists(final_cover) else base_image

        print(f"🎬 正在合成 MP4 影片，使用標題封面: {used_image}...")
        audio_clip = AudioFileClip(audio_file)
        video_clip = ImageClip(used_image, duration=audio_clip.duration)
        video_clip.audio = audio_clip
        
        video_clip.write_videofile(video_output, fps=24, codec='libx264', audio_codec='aac')
        print(f"✅ 成功生成終極 MP4 影片: {video_output}")

        audio_clip.close()
        video_clip.close()
        if os.path.exists(audio_file):
            os.remove(audio_file)
            print(f"🧹 已自動清理臨時音檔: {audio_file}")

    except Exception as e:
        print(f"⚠️ MP4 合成失敗: {e}")

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        mix_chapter("input.txt", 'boy', "temp_Pboy.mp3")
        generate_mp4("temp_Pboy.mp3", "genesis_ch1_Pboy.mp4", "input.txt")

        mix_chapter("input.txt", 'girl', "temp_Pgirl.mp3")
        generate_mp4("temp_Pgirl.mp3", "genesis_ch1_Pgirl.mp4", "input.txt")
