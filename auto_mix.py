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
        
        # 建立半透明暗色黑底條帶，確保對比度
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        rect_top = int(height * 0.32)
        rect_bottom = int(height * 0.68)
        draw.rectangle([(0, rect_top), (width, rect_bottom)], fill=(0, 0, 0, 170))
        
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        # 設定超大高清字體 (比例大幅提升)
        brand_font_size = int(height * 0.08)   # 招牌字體大小
        title_font_size = int(height * 0.12)   # 標題大字大小
        
        if font_file:
            brand_font = ImageFont.truetype(font_file, brand_font_size)
            title_font = ImageFont.truetype(font_file, title_font_size)
        else:
            brand_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            
        brand_text = "★ 廣東話聖經劇場 ★"
        
        # 繪製金色招牌 (正中間偏上)
        draw.text((width / 2, height * 0.42), brand_text, font=brand_font, fill=(255, 215, 0), anchor="mm")
        # 繪製純白加粗標題 (正中間偏下)
        draw.text((width / 2, height * 0.58), title_text, font=title_font, fill=(255, 255, 255), anchor="mm")
        
        img.save(output_image_path)
        print(f"🎨 已成功生成高清居中標題封面: {output_image_path}")
        return True
    except Exception as e:
        print(f"⚠️ 生成標題封面失敗: {e}")
        return False

async def generate_tts(text, voice, output_mp3):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    if not clean_text:
        return False

    for attempt in range(8):
        try:
            communicate = edge_tts.Communicate(clean_text, voice, rate='-20%')
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1000:
                print(f"✅ [{voice}] 語音合成成功！")
                return True
        except Exception as e:
            print(f"⚠️ [{voice}] 重試第 {attempt+1} 次...")
            await asyncio.sleep(3)
    return False

def mix_chapter(text_file, gender, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    
    # 解析 BGM 轉場、SFX 段落同 TITLE
    combined_elements = []
    
    # 1. 偵測段落 BGM 轉場標籤
    bgm_sections = []
    current_bgm_type = 'calm'
    
    # 2. 偵測段落 SFX 段落標籤
    pattern_sfx = r'(\[雷雨\]|\[雷聲\]|\[雨聲雷鳴\]|\[風雨雷電\]|\[下雨\]|\[雨聲\]|\[海洋\]|\[海浪\]|\[海浪風鈴\]|\[柴火\]|\[溫暖\]|\[森林\]|\[天地\]|\[森林鳥鳴\]|\[風鈴\]|\[海鳥\]|\[溪流\]|\[流水\]|\[戰爭\]|\[交戰\]|\[洞穴\]|\[水滴\])'
    parts_sfx = re.split(pattern_sfx, raw_content)
    
    combined_voice_sfx = []
    for part in parts_sfx:
        if not part.strip(): continue
        
        # 3. 偵測段落 BGM 段落標籤
        bgm_match = re.search(r'\[BGM\s*:\s*(happy|calm|sad)\]', part, re.IGNORECASE)
        if bgm_match:
            current_bgm_type = bgm_match.group(1).lower()
            print(f"🎵 新版偵測：發現 BGM 轉場 -> {current_bgm_type}")
            # 去除 part 入面嘅 標籤
            clean_part = re.sub(r'\[BGM\s*:\s*(happy|calm|sad)\]', '', part, re.IGNORECASE).strip()
            # 將剩餘嘅 clean_part 用 SFX 段落標籤記低音樂
            # 由於 part 本身有可能仲帶有 SFX 段落標籤，所以要重新解析
            if clean_part:
                sub_parts_sfx = re.split(pattern_sfx, clean_part)
                for sub_part in sub_parts_sfx:
                    if not sub_part.strip(): continue
                    if sub_part in TAG_AUDIO_MAP:
                        # part 本身就係 SFX 段落標籤
                        combined_voice_sfx.append((sub_part, None, current_bgm_type))
                    else:
                        combined_voice_sfx.append((None, sub_part.strip(), current_bgm_type))
        elif part in TAG_AUDIO_MAP:
             # part 本身就係 SFX 段落標籤
             combined_voice_sfx.append((part, None, current_bgm_type))
        elif not re.match(r'\[TITLE\s*:', part, re.IGNORECASE):
             combined_voice_sfx.append((None, part.strip(), current_bgm_type))

    if not combined_voice_sfx:
        combined_voice_sfx = [(None, raw_content.strip(), 'calm')]

    combined_voice = AudioSegment.silent(duration=0)
    combined_sfx = AudioSegment.silent(duration=0)
    combined_bgm = AudioSegment.silent(duration=0) # 新版用分段音樂

    created_temp_files = []

    print(f"🔊 升級版程式：正在處理分段音樂轉場...")
    current_active_bgm = None
    bgm_filename = None

    for idx, (tag_sfx, text_tts, tag_bgm_type) in enumerate(combined_voice_sfx):
        seg_dur = 0
        
        # 處理 TTS 分段
        if text_tts:
            temp_file = f"temp_{gender}_{idx}.mp3"
            created_temp_files.append(temp_file)
            success = asyncio.run(generate_tts(text_tts, voice, temp_file))
            
            if success and os.path.exists(temp_file):
                raw_voice = AudioSegment.from_file(temp_file)
                combined_voice += raw_voice + AudioSegment.silent(duration=1500)
                seg_dur = len(raw_voice) + 1500
        
        # 處理 SFX 分段
        seg_sfx = AudioSegment.silent(duration=seg_dur)
        if tag_sfx and tag_sfx in TAG_AUDIO_MAP:
            sfx_filename = TAG_AUDIO_MAP[tag_sfx]
            if os.path.exists(sfx_filename):
                snd = AudioSegment.from_file(sfx_filename)
                snd_looped = (snd * (int(seg_dur / len(snd)) + 1))[:seg_dur] - 22
                seg_sfx = snd_looped.fade_in(500).fade_out(1000)
        combined_sfx += seg_sfx
        
        # 處理 BGM 分段
        bgm_music_track = AudioSegment.silent(duration=seg_dur)
        music_filename = MUSIC_MAP.get(tag_bgm_type, 'music_calm.mp3')
        if music_filename and os.path.exists(music_filename):
            bgm_music = AudioSegment.from_file(music_filename)
            
            target_loudness = -22.0
            change_in_dBFS = target_loudness - bgm_music.dBFS
            bgm_music = bgm_music.apply_gain(change_in_dBFS)
            
            music_looped = (bgm_music * (int(seg_dur / len(bgm_music)) + 1))[:seg_dur]
            bgm_music_track = music_looped.fade_out(1500)
        combined_bgm += bgm_music_track

    # 清理臨時音檔
    for t_file in created_temp_files:
        if os.path.exists(t_file):
            os.remove(t_file)

    if len(combined_voice) == 0:
        print(f"❌ {gender} ({voice}) 語音生成失敗。")
        return

    # 由於 combined_bgm 段落音樂係分開 looped 嘅，佢哋轉場會好流暢
    final_mix = combined_bgm.overlay(combined_sfx).overlay(combined_voice, position=1000)
    final_mix.export(output_filename, format="mp3")
    print(f"🎉 升級版臨時音訊混音完成: {output_filename}")

def generate_mp4(audio_file, video_output, text_file="input.txt"):
    try:
        from moviepy import AudioFileClip, ImageClip
        
        base_image = 'cover.png' if os.path.exists('cover.png') else 'default_cover.png'
        if not os.path.exists(base_image):
            print(f"⚠️ 找不到封面圖片 ({base_image})，跳過 MP4 合成。")
            return

        # 抓取 input.txt 第一行標題
        title_text = "創世記 第一章"
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                title_match = re.search(r'\[TITLE\s*:\s*(.*?)\]', content, re.IGNORECASE)
                if title_match:
                    title_text = title_match.group(1).strip()

        # 生成標題封面
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
        # 1. 處理 P仔 (boy)
        mix_chapter("input.txt", 'boy', "temp_Pboy.mp3")
        generate_mp4("temp_Pboy.mp3", "genesis_ch1_Pboy.mp4", "input.txt")

        # 2. 處理 P女 (girl)
        mix_chapter("input.txt", 'girl', "temp_Pgirl.mp3")
        generate_mp4("temp_Pgirl.mp3", "genesis_ch1_Pgirl.mp4", "input.txt")
