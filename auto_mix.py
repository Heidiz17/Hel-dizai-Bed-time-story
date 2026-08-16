import os
import re
import asyncio
import edge_tts
from pydub import AudioSegment

TAG_AUDIO_MAP = {
    '[下雨]': ['rain.mp3'],
    '[雷雨]': ['rain.mp3', 'thunder.mp3'],
    '[海洋]': ['wave.mp3', 'windbell.mp3'],
    '[溫暖]': ['fire.mp3', 'rain.mp3'],
    '[天地]': ['forest.mp3', 'rain.mp3'],
    '[海鳥]': ['wave.mp3', 'forest.mp3']
}

MUSIC_MAP = {
    'happy': 'music_happy.mp3',
    'sad': 'music_sad.mp3',
    'calm': 'music_calm.mp3'
}

VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',
    'girl': 'zh-HK-HiuiuNeural'
}

async def generate_tts(text, voice, output_mp3):
    # 徹底清除標籤與特殊字元，只留純廣東話文字
    clean_text = re.sub(r'\[.*?\]', '', text)
    clean_text = clean_text.strip()
    
    if not clean_text:
        clean_text = "創世記第一章"

    # 嘗試合成，若網絡微卡自動重試 3 次
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 0:
                return
        except Exception as e:
            print(f"TTS 合成重試第 {attempt+1} 次: {e}")
            await asyncio.sleep(2)

def mix_chapter(text_file, gender, bg_music_type, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    voice_file = f"temp_{gender}.mp3"
    asyncio.run(generate_tts(content, voice, voice_file))

    if not os.path.exists(voice_file) or os.path.getsize(voice_file) == 0:
        print(f"⚠️ {gender} 人聲生成失敗，跳過混音。")
        return

    voice_segment = AudioSegment.from_file(voice_file)
    total_duration = len(voice_segment) + 4000

    base_bg = AudioSegment.silent(duration=total_duration)

    for tag, audio_files in TAG_AUDIO_MAP.items():
        if tag in content:
            for a_file in audio_files:
                if os.path.exists(a_file):
                    snd = AudioSegment.from_file(a_file)
                    snd_looped = (snd * (int(total_duration / len(snd)) + 1))[:total_duration] - 12
                    base_bg = base_bg.overlay(snd_looped)
            break

    music_filename = MUSIC_MAP.get(bg_music_type)
    if music_filename and os.path.exists(music_filename):
        bg_music = AudioSegment.from_file(music_filename)
        music_looped = (bg_music * (int(total_duration / len(bg_music)) + 1))[:total_duration] - 15
        base_bg = base_bg.overlay(music_looped)

    final_mix = base_bg.overlay(voice_segment, position=1000)
    final_mix.export(output_filename, format="mp3")

    if os.path.exists(voice_file):
        os.remove(voice_file)

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        print("⚡ 正在生成 P仔 男聲版...")
        mix_chapter("input.txt", "boy", "happy", "genesis_ch1_Pboy.mp3")
        
        print("⚡ 正在生成 P女 女聲版...")
        mix_chapter("input.txt", "girl", "happy", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本純淨混音完美完成！")
