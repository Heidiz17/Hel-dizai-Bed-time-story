import os
import re
import asyncio
import sys
import time
import edge_tts
from pydub import AudioSegment

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
        if re.match(r'\[BGM\s*:', part, re.IGNORECASE):
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

def generate_mp4(audio_file, video_output):
    try:
        from moviepy import AudioFileClip, ImageClip
        
        image_file = 'cover.png' if os.path.exists('cover.png') else 'default_cover.png'
        
        if not os.path.exists(image_file):
            print(f"⚠️ 找不到封面圖片 ({image_file})，跳過 MP4 合成。")
            return

        print(f"🎬 正在合成 MP4 影片，使用封面: {image_file}...")
        audio_clip = AudioFileClip(audio_file)
        video_clip = ImageClip(image_file).set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
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
        generate_mp4("temp_Pboy.mp3", "genesis_ch1_Pboy.mp4")

        # 2. 處理 P女 (girl)
        mix_chapter("input.txt", 'girl', "temp_Pgirl.mp3")
        generate_mp4("temp_Pgirl.mp3", "genesis_ch1_Pgirl.mp4")
