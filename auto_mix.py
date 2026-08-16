import os
import re
import asyncio
import time
import edge_tts
from pydub import AudioSegment

TAG_AUDIO_MAP = {
    '[雷雨]': ['thunder.mp3', 'rain.mp3'],
    '[雨聲雷鳴]': ['thunder.mp3', 'rain.mp3'],
    '[風雨雷電]': ['thunder.mp3', 'rain.mp3'],
    '[下雨]': ['rain.mp3'],
    '[雨夜柴火]': ['rain.mp3', 'fire.mp3'],
    '[海洋]': ['wave.mp3'],
    '[海浪風鈴]': ['wave.mp3', 'windbell.mp3'],
    '[柴火]': ['fire.mp3'],
    '[溫暖]': ['fire.mp3'],
    '[森林]': ['forest.mp3'],
    '[天地]': ['forest.mp3'],
    '[森林鳥鳴]': ['forest.mp3', 'windbell.mp3'],
    '[風鈴]': ['windbell.mp3'],
    '[海鳥]': ['windbell.mp3']
}

MUSIC_MAP = {
    'happy': 'music_happy.mp3',
    'sad': 'music_sad.mp3',
    'calm': 'music_calm.mp3'
}

VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',   # P仔 雲傑男聲
    'girl': 'zh-HK-HiuiuNeural'    # P女 曉佳女聲
}

async def generate_tts(text, voice, output_mp3):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    if not clean_text:
        clean_text = "廣東話聖經朗讀"

    # rate='-20%' 放慢語速 20%
    for attempt in range(5):
        try:
            communicate = edge_tts.Communicate(clean_text, voice, rate='-20%')
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1000:
                print(f"✅ {voice} 成功生成音檔，大小: {os.path.getsize(output_mp3)} bytes")
                return
        except Exception as e:
            print(f"⚠️ TTS 合成 ({voice}) 第 {attempt+1} 次失敗，正在重試: {e}")
            await asyncio.sleep(4)

def mix_chapter(text_file, gender, bg_music_type, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    voice_file = f"temp_voice_{gender}.mp3"
    
    if os.path.exists(voice_file):
        os.remove(voice_file)

    asyncio.run(generate_tts(content, voice, voice_file))

    if not os.path.exists(voice_file) or os.path.getsize(voice_file) < 1000:
        print(f"❌ {gender} ({voice}) 最終生成失敗，無法進行混音。")
        return

    voice_segment = AudioSegment.from_file(voice_file)
    total_duration = len(voice_segment) + 3000

    base_bg = AudioSegment.silent(duration=total_duration)

    selected_files = []
    for tag, audio_files in TAG_AUDIO_MAP.items():
        if tag in content:
            selected_files = audio_files
            break

    if not selected_files and os.path.exists('fire.mp3'):
        selected_files = ['fire.mp3']

    # 大自然音效降至 20% (-22dB) + 淡出 2 秒
    for a_file in selected_files:
        if os.path.exists(a_file):
            snd = AudioSegment.from_file(a_file)
            snd_looped = (snd * (int(total_duration / len(snd)) + 1))[:total_duration] - 22
            snd_looped = snd_looped.fade_out(2000)
            base_bg = base_bg.overlay(snd_looped)

    # 背景音樂 (-24dB) + 淡出 2 秒
    music_filename = MUSIC_MAP.get(bg_music_type)
    if music_filename and os.path.exists(music_filename):
        bg_music = AudioSegment.from_file(music_filename)
        music_looped = (bg_music * (int(total_duration / len(bg_music)) + 1))[:total_duration] - 24
        music_looped = music_looped.fade_out(2000)
        base_bg = base_bg.overlay(music_looped)

    final_mix = base_bg.overlay(voice_segment, position=1000)
    final_mix.export(output_filename, format="mp3")

    if os.path.exists(voice_file):
        os.remove(voice_file)

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        print("⚡ 1/2 正在生成 P仔 男聲版...")
        mix_chapter("input.txt", "boy", "happy", "genesis_ch1_Pboy.mp3")
        
        print("⏳ 避開伺服器頻率限制，休息 5 秒...")
        time.sleep(5)
        
        print("⚡ 2/2 正在生成 P女 女聲版...")
        mix_chapter("input.txt", "girl", "happy", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本生成完成！")
