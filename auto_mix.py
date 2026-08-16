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
    'girl': 'zh-HK-HiuiuNeural'    # P女 曉佳女聲
}

# 音訊精準降速函數 (放慢 20% = speed 0.8)
def slow_down_audio(segment, speed=0.8):
    sound_with_altered_frame_rate = segment._spawn(segment.raw_data, overrides={
        "frame_rate": int(segment.frame_rate * speed)
    })
    return sound_with_altered_frame_rate.set_frame_rate(segment.frame_rate)

async def generate_tts(text, voice, output_mp3):
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    if not clean_text:
        return False

    for attempt in range(5):
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(output_mp3)
            if os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 1000:
                return True
        except Exception as e:
            await asyncio.sleep(2)
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

    for idx, (tag, text) in enumerate(sections):
        temp_file = f"temp_{gender}_{idx}.mp3"
        success = asyncio.run(generate_tts(text, voice, temp_file))
        
        if not success or not os.path.exists(temp_file):
            continue

        raw_voice = AudioSegment.from_file(temp_file)
        
        # 關鍵精準降速：強行將人聲音訊精確放慢 20% (0.8x 速度)
        slow_voice = slow_down_audio(raw_voice, speed=0.8)
        
        seg_dur = len(slow_voice) + 1500
        
        a_file = TAG_AUDIO_MAP.get(tag, 'fire.mp3')
        seg_bg = AudioSegment.silent(duration=seg_dur)

        if os.path.exists(a_file):
            snd = AudioSegment.from_file(a_file)
            snd_looped = (snd * (int(seg_dur / len(snd)) + 1))[:seg_dur] - 22 # 20% 微音量 (-22dB)
            seg_bg = snd_looped

        combined_voice += slow_voice + AudioSegment.silent(duration=1500)
        combined_bg += seg_bg

        if os.path.exists(temp_file):
            os.remove(temp_file)

    if len(combined_voice) == 0:
        print(f"❌ {gender} 語音生成失敗。")
        return

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
        print("⚡ 正在生成 P仔 男聲版 (音訊強行精準減速20%)...")
        mix_chapter("input.txt", "boy", "happy", "genesis_ch1_Pboy.mp3")
        
        time.sleep(4)
        
        print("⚡ 正在生成 P女 女聲版 (音訊強行精準減速20%)...")
        mix_chapter("input.txt", "girl", "happy", "genesis_ch1_Pgirl.mp3")
        
        print("🎉 雙版本精準放慢20%混音完成！")
