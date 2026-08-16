import os
import re
import asyncio
import time
import edge_tts
from pydub import AudioSegment

TAG_AUDIO_MAP = {
    '[雷雨]': 'thunder.mp3',
    '[雨聲雷鳴]': 'thunder.mp3',
    '[風雨雷電]': 'thunder.mp3',
    '[下雨]': 'rain.mp3',
    '[雨夜柴火]': 'rain.mp3',
    '[海洋]': 'wave.mp3',
    '[海浪風鈴]': 'wave.mp3',
    '[柴火]': 'fire.mp3',
    '[溫暖]': 'fire.mp3',
    '[森林]': 'forest.mp3',
    '[天地]': 'forest.mp3',
    '[森林鳥鳴]': 'forest.mp3',
    '[風鈴]': 'windbell.mp3',
    '[海鳥]': 'windbell.mp3'
}

MUSIC_MAP = {
    'happy': 'music_happy.mp3',
    'sad': 'music_sad.mp3',
    'calm': 'music_calm.mp3'
}

VOICE_MAP = {
    'boy': 'zh-HK-WanLungNeural',   # P仔 雲傑男聲
    'girl': 'zh-HK-SiuMingNeural'   # P女 小明女聲
}

async def generate_tts(text, voice, output_mp3):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    if not clean_text:
        return False

    # 加強版重試 8 次，解決女聲引擎偶發性連線失敗問題
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

def mix_chapter(text_file, gender, bg_music_type, output_filename):
    with open(text_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    voice = VOICE_MAP.get(gender, 'zh-HK-WanLungNeural')
    
    pattern = r'(\[.*?\])'
    parts = re.split(pattern, raw_content)
    
    sections = []
    current_tag = None
    
    for part in parts:
        if not part.strip():
            continue
        if part in TAG_AUDIO_MAP or part.startswith('['):
            current_tag = part
        else:
            sections.append((current_tag, part.strip()))

    if not sections:
        sections = [(None, raw_content.strip())]

    combined_voice = AudioSegment.silent(duration=0)
    combined_bg = AudioSegment.silent(duration=0)
    created_temp_files = []

    for idx, (tag, text) in enumerate(sections):
        temp_file = f"temp_{gender}_{idx}.mp3"
        created_temp_files.append(temp_file)
        success = asyncio.run(generate_tts(text, voice, temp_file))
        
        if not success or not os.path.exists(temp_file):
            continue

        raw_voice = AudioSegment.from_file(temp_file)
        seg_dur = len(raw_voice) + 1500
        
        # 零疊加單一音效，20% 微音量 (-22dB)
        a_file = TAG_AUDIO_MAP.get(tag, 'fire.mp3')
        seg_bg = AudioSegment.silent(duration=seg_dur)

        if os.path.exists(a_file):
            snd = AudioSegment.from_file(a_file)
            snd_looped = (snd * (int(seg_dur / len(snd)) + 1))[:seg_dur] - 22
            seg_bg = snd_looped

        combined_voice += raw_voice + AudioSegment.silent(duration=1500)
        combined_bg += seg_bg

    for t_file in created_temp_files:
        if os.path.exists(t_file):
            os.remove(t_file)

    if len(combined_voice) == 0:
        print(f"❌ {gender} ({voice}) 語音生成失敗。")
        return

    # 結尾自然淡出
    total_dur = len(combined_voice) + 3000
    final_bg = combined_bg[:total_dur]
    
    music_filename = MUSIC_MAP.get(bg_music_type)
    if music_filename and os.path.exists(music_filename):
        bg_music = AudioSegment.from_file(music_filename)
        music_looped = (bg_music * (int(total_dur / len(bg_music)) + 1))[:total_dur] - 24
        music_looped = music_looped.fade_out(2000)
        final_bg = final_bg.overlay(music_looped)

    final_mix = final_bg.overlay(combined_voice, position=1000)
    final_mix.export(output_filename, format="mp3")

if __name__ == "__main__":
    if os.path.exists("input.txt"):
        print("⚡ 1/2 正在生成 P仔 男聲版 (雲傑 - 高清原聲 -20%語速)...")
        mix_chapter("input.txt", "boy", "calm", "genesis_ch1_Pboy.mp3")
        
        print("⏳ 避開伺服器頻率限制，休息 6 秒...")
        time.sleep(6)
        
        print("⚡ 2/2 正在生成 P女 女聲版 (小明 - 高清原聲 -20%語速)...")
        mix_chapter("input.txt", "girl", "calm", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本高清純淨混音完成！")
