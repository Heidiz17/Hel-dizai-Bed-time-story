import os
import re
import asyncio
import edge_tts
from pydub import AudioSegment

# 1. 6大標籤與大自然音效檔案對應表 (支援單重與雙重音效)
TAG_AUDIO_MAP = {
    '[下雨]': ['rain.mp3'],
    '[雷雨]': ['rain.mp3', 'thunder.mp3'],
    '[海洋]': ['wave.mp3', 'windbell.mp3'],
    '[溫暖]': ['fire.mp3', 'rain.mp3'],
    '[天地]': ['forest.mp3', 'rain.mp3'],
    '[海鳥]': ['wave.mp3', 'forest.mp3']
}

# 2. 3 隻背景音樂預留檔名 (happy / sad / calm)
MUSIC_MAP = {
    'happy': 'music_happy.mp3', # 代表 Happy / 平安讚美
    'sad': 'music_sad.mp3',     # 代表 肅穆 / 哀傷
    'calm': 'music_calm.mp3'    # 代表 Carmen 靜心 / 冥想
}

# 3. 語音引擎 (P仔男聲 & P女女聲)
VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',   # P仔 雲傑男聲
    'girl': 'zh-HK-HiuiuNeural'    # P女 曉佳女聲
}

async def generate_tts(text, voice, output_mp3):
    # 清理文字中的標籤，只保留純廣東話文字給 Edge-TTS 朗讀
    clean_text = re.sub(r'\[.*?\]', '', text)
    communicate = edge_tts.Communicate(clean_text, voice)
    await communicate.save(output_mp3)

def mix_chapter(text_file, gender, bg_music_type, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 生成廣東話人聲 (P仔/P女)
    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    voice_file = f"temp_{gender}.mp3"
    asyncio.run(generate_tts(content, voice, voice_file))

    voice_segment = AudioSegment.from_file(voice_file)
    total_duration = len(voice_segment) + 4000 # 結尾留白 4 秒

    # 2. 建立靜音底軌 (長度跟隨廣東話人聲)
    base_bg = AudioSegment.silent(duration=total_duration)

    # 3. 根據標籤自動疊加上大自然音效
    for tag, audio_files in TAG_AUDIO_MAP.items():
        if tag in content:
            for a_file in audio_files:
                if os.path.exists(a_file):
                    snd = AudioSegment.from_file(a_file)
                    # 循環播放音效至覆蓋整集長度
                    snd_looped = (snd * (int(total_duration / len(snd)) + 1))[:total_duration] - 12
                    base_bg = base_bg.overlay(snd_looped)
            break

    # 4. 疊加背景音樂 (happy / sad / calm，若有檔案自動融合)
    music_filename = MUSIC_MAP.get(bg_music_type)
    if music_filename and os.path.exists(music_filename):
        bg_music = AudioSegment.from_file(music_filename)
        music_looped = (bg_music * (int(total_duration / len(bg_music)) + 1))[:total_duration] - 15
        base_bg = base_bg.overlay(music_looped)

    # 5. 將人聲與純淨背景音效 (自然聲+背景樂) 完美混音
    final_mix = base_bg.overlay(voice_segment, position=1000)
    final_mix.export(output_filename, format="mp3")

    # 清理臨時檔
    if os.path.exists(voice_file):
        os.remove(voice_file)

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        print("⚡ 正在生成 P仔 男聲版...")
        mix_chapter("input.txt", "boy", "happy", "genesis_ch1_Pboy.mp3")
        
        print("⚡ 正在生成 P女 女聲版...")
        mix_chapter("input.txt", "girl", "happy", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本純淨混音完美完成！")
