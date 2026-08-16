import os
import re
import asyncio
import edge_tts
from pydub import AudioSegment

# 1. 完整音效標籤庫 (支援單重、雙重及三重疊加)
TAG_AUDIO_MAP = {
    # 單重音效
    '[下雨]': ['rain.mp3'],
    '[雷雨]': ['thunder.mp3'],
    '[海洋]': ['wave.mp3'],
    '[柴火]': ['fire.mp3'],
    '[溫暖]': ['fire.mp3'],
    '[森林]': ['forest.mp3'],
    '[天地]': ['forest.mp3'],
    '[風鈴]': ['windbell.mp3'],
    '[海鳥]': ['windbell.mp3'],
    
    # 雙重及多重複合音效
    '[雨聲雷鳴]': ['rain.mp3', 'thunder.mp3'],
    '[海浪風鈴]': ['wave.mp3', 'windbell.mp3'],
    '[雨夜柴火]': ['fire.mp3', 'rain.mp3'],
    '[森林鳥鳴]': ['forest.mp3', 'windbell.mp3'],
    '[森林雨聲]': ['forest.mp3', 'rain.mp3'],
    '[風雨雷電]': ['rain.mp3', 'thunder.mp3', 'windbell.mp3']
}

# 2. 3 款背景音樂
MUSIC_MAP = {
    'happy': 'music_happy.mp3',
    'sad': 'music_sad.mp3',
    'calm': 'music_calm.mp3'
}

# 3. 語音引擎
VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',   # P仔 雲傑男聲
    'girl': 'zh-HK-HiuiuNeural'    # P女 曉佳女聲
}

async def generate_tts(text, voice, output_mp3):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    if not clean_text:
        clean_text = "廣東話聖經朗讀"

    # rate='-10%' 放慢語速，平穩莊嚴
    for attempt in range(5):
        try:
            communicate = edge_tts.Communicate(clean_text, voice, rate='-10%')
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1000:
                return
        except Exception as e:
            print(f"TTS 合成 ({voice}) 重試第 {attempt+1} 次: {e}")
            await asyncio.sleep(3)

def mix_chapter(text_file, gender, bg_music_type, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    voice_file = f"temp_voice_{gender}.mp3"
    
    if os.path.exists(voice_file):
        os.remove(voice_file)

    asyncio.run(generate_tts(content, voice, voice_file))

    if not os.path.exists(voice_file) or os.path.getsize(voice_file) < 1000:
        print(f"⚠️ {gender} 人聲生成失敗，跳過混音。")
        return

    voice_segment = AudioSegment.from_file(voice_file)
    total_duration = len(voice_segment) + 4000

    base_bg = AudioSegment.silent(duration=total_duration)

    # 標籤比對與音效疊加
    has_tag = False
    for tag, audio_files in TAG_AUDIO_MAP.items():
        if tag in content:
            has_tag = True
            for a_file in audio_files:
                if os.path.exists(a_file):
                    snd = AudioSegment.from_file(a_file)
                    snd_looped = (snd * (int(total_duration / len(snd)) + 1))[:total_duration] - 12
                    base_bg = base_bg.overlay(snd_looped)

    # 無標籤時，預設使用 fire.mp3（上帝溫柔烈火）
    if not has_tag and os.path.exists('fire.mp3'):
        snd = AudioSegment.from_file('fire.mp3')
        snd_looped = (snd * (int(total_duration / len(snd)) + 1))[:total_duration] - 10
        base_bg = base_bg.overlay(snd_looped)

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
        
        import time
        time.sleep(3)
        
        print("⚡ 正在生成 P女 女聲版...")
        mix_chapter("input.txt", "girl", "happy", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本純淨混音完成！")
