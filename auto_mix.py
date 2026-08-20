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
    font_path = "CustomFont.ttf"
    if not os.path.exists(font_path):
        print("📥 正在下載中文字型檔 (Noto Sans CJK)...")
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChineseHK/NotoSansCJKhk-Bold.otf"
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception:
            pass
    return font_path if os.path.exists(font_path) else None

def create_title_cover(base_image_path, title_text, output_image_path):
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
        return True
    except Exception as e:
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
                return True
        except Exception:
            await asyncio.sleep(2)
    return False

def mix_chapter(text_file, gender, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    
    # 按行嚴格順序解析
    lines = raw_content.split('\n')
    current_bgm = 'calm' # 預設第一段為 calm
    current_sfx = None
    
    parsed_tasks = [] # 每筆資料格式: (bgm_type, sfx_tag, text)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 過濾 TITLE
        if re.match(r'\[TITLE\s*:', line, re.IGNORECASE):
            continue
            
        # 1. 精準順序偵測 BGM 切換
        bgm_match = re.search(r'\[BGM\s*:\s*(happy|calm|sad)\]', line, re.IGNORECASE)
        if bgm_match:
            current_bgm = bgm_match.group(1).lower()
            print(f"🎵 順序解析：發現 BGM 轉場 -> 切換為 [{current_bgm}]")
            line = re.sub(r'\[BGM\s*:\s*(happy|calm|sad)\]', '', line, re.IGNORECASE).strip()

        if not line:
            continue

        # 2. 精準順序偵測 SFX 切換
        sfx_match = re.search(r'(\[.*?\])', line)
        if sfx_match:
            tag = sfx_match.group(1)
            if tag in TAG_AUDIO_MAP:
                current_sfx = tag
                line = line.replace(tag, '').strip()

        clean_text = re.sub(r'\[.*?\]', '', line).strip()
        if clean_text:
            parsed_tasks.append((current_bgm, current_sfx, clean_text))

    combined_voice = AudioSegment.silent(duration=0)
    combined_sfx = AudioSegment.silent(duration=0)
    combined_bgm = AudioSegment.silent(duration=0)
    created_temp_files = []

    print(f"🔊 開始進行精準時間軸混音 (共 {len(parsed_tasks)} 段)...")

    for idx, (bgm_type, sfx_tag, text) in enumerate(parsed_tasks):
        temp_file = f"temp_{gender}_{idx}.mp3"
        created_temp_files.append(temp_file)
        
        success = asyncio.run(generate_tts(text, voice, temp_file))
        if not success or not os.path.exists(temp_file):
            continue

        raw_voice = AudioSegment.from_file(temp_file)
        seg_dur = len(raw_voice) + 1500  # 每句語音時間 + 1.5秒停頓
        
        # 1. 疊加語音
        combined_voice += raw_voice + AudioSegment.silent(duration=1500)

        # 2. 疊加當前 SFX
        seg_sfx = AudioSegment.silent(duration=seg_dur)
        if sfx_tag and sfx_tag in TAG_AUDIO_MAP:
            sfx_file = TAG_AUDIO_MAP[sfx_tag]
            if os.path.exists(sfx_file):
                snd = AudioSegment.from_file(sfx_file)
                snd_looped = (snd * (int(seg_dur / len(snd)) + 1))[:seg_dur] - 22
                seg_sfx = snd_looped.fade_in(300).fade_out(800)
        combined_sfx += seg_sfx

        # 3. 精準疊加當前句子的 BGM (該段是 calm 就用 calm，是 sad 就用 sad)
        seg_bgm = AudioSegment.silent(duration=seg_dur)
        bgm_file = MUSIC_MAP.get(bgm_type, 'music_calm.mp3')
        if bgm_file and os.path.exists(bgm_file):
            bg_music = AudioSegment.from_file(bgm_file)
            target_loudness = -22.0
            bg_music = bg_music.apply_gain(target_loudness - bg_music.dBFS)
            
            music_looped = (bg_music * (int(seg_dur / len(bg_music)) + 1))[:seg_dur]
            seg_bgm = music_looped.fade_in(300).fade_out(300)
        combined_bgm += seg_bgm

    # 清理臨時檔
    for t_file in created_temp_files:
        if os.path.exists(t_file):
            os.remove(t_file)

    if len(combined_voice) == 0:
        print(f"❌ {gender} 語音合成失敗。")
        return

    total_dur = len(combined_voice) + 2000
    final_mix = combined_bgm[:total_dur].overlay(combined_sfx[:total_dur]).overlay(combined_voice, position=1000)
    final_mix.export(output_filename, format="mp3")
    print(f"🎉 成功完成【開局 Calm、中途 Sad】動態混音檔: {output_filename}")

def generate_mp4(audio_file, video_output, text_file="input.txt"):
    try:
        from moviepy import AudioFileClip, ImageClip
        
        base_image = 'cover.png' if os.path.exists('cover.png') else 'default_cover.png'
        if not os.path.exists(base_image):
            return

        title_text = "創世記 第六章"
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                title_match = re.search(r'\[TITLE\s*:\s*(.*?)\]', content, re.IGNORECASE)
                if title_match:
                    title_text = title_match.group(1).strip()

        final_cover = "final_cover_with_title.png"
        create_title_cover(base_image, title_text, final_cover)
        used_image = final_cover if os.path.exists(final_cover) else base_image

        audio_clip = AudioFileClip(audio_file)
        video_clip = ImageClip(used_image, duration=audio_clip.duration)
        video_clip.audio = audio_clip
        
        video_clip.write_videofile(video_output, fps=24, codec='libx264', audio_codec='aac')
        print(f"✅ 終極 MP4 影片生成成功: {video_output}")

        audio_clip.close()
        video_clip.close()
        if os.path.exists(audio_file):
            os.remove(audio_file)

    except Exception as e:
        print(f"⚠️ MP4 合成失敗: {e}")

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        mix_chapter("input.txt", 'boy', "temp_Pboy.mp3")
        generate_mp4("temp_Pboy.mp3", "genesis_ch6_Pboy.mp4", "input.txt")

        mix_chapter("input.txt", 'girl', "temp_Pgirl.mp3")
        generate_mp4("temp_Pgirl.mp3", "genesis_ch6_Pgirl.mp4", "input.txt")
