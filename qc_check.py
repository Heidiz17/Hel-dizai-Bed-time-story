import os
from pydub import AudioSegment
from pydub.silence import detect_silence

def check_video_pauses(mp4_filename):
    print(f"🎬 正在讀取影片音軌進行極速 QC 掃描: {mp4_filename} ...")
    
    if not os.path.exists(mp4_filename):
        print(f"❌ 錯誤：找不到檔案 {mp4_filename}")
        return

    # 1. 直接從 MP4 提取音訊
    audio = AudioSegment.from_file(mp4_filename, format="mp4")
    total_duration_sec = len(audio) / 1000.0
    print(f"⏱️ 影片總時長: {total_duration_sec:.2f} 秒\n")
    print("=" * 50)
    print("📊 正在偵測所有停頓與呼吸區間 (支援極細微停頓)...")

    # 2. 使用 pydub 的 detect_silence 演算法
    # min_silence_len = 200 (只要停頓超過 0.2 秒就捉)
    # silence_thresh = audio.dBFS - 16 (自動根據整段音訊平均音量計算安靜門檻)
    silence_thresh = audio.dBFS - 16
    min_silence_len = 200 

    silences = detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

    if not silences:
        print("⚠️ 未偵測到明顯停頓。")
    else:
        for idx, (start_ms, end_ms) in enumerate(silences):
            start_sec = start_ms / 1000.0
            end_sec = end_ms / 1000.0
            duration_sec = (end_ms - start_ms) / 1000.0
            
            # 只列出持續時間大於 0.15 秒的有效停頓
            if duration_sec >= 0.15:
                print(f"  [停頓 #{idx+1}] 開始: {start_sec:.2f}s ➔ 結束: {end_sec:.2f}s (停頓長度: {duration_sec:.2f}s)")

    print("=" * 50)
    print("✨ 演算法 QC 掃描完畢！新城永遠品質！")

if __name__ == "__main__":
    # 你可以隨時修改你想 QC 的 MP4 檔案名稱
    target_video = "genesis_ch1_Pgirl.mp4" 
    check_video_pauses(target_video)
