"""快速测试 faster-whisper 转录"""
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stt.transcribe import extract_audio, transcribe

if len(sys.argv) < 2:
    print("用法: python test_whisper.py <video_or_audio>")
    sys.exit(1)

input_path = sys.argv[1]
out_dir = "tmp/test_whisper"
os.makedirs(out_dir, exist_ok=True)

# 如果输入是视频，先提音频
if input_path.lower().endswith((".mp4", ".mov", ".mkv", ".avi")):
    print("提取音频...")
    audio_path = extract_audio(input_path, out_dir)
else:
    audio_path = input_path

print(f"开始转录: {audio_path}")
model = sys.argv[2] if len(sys.argv) > 2 else "large-v3-turbo"
srt_path = transcribe(audio_path, out_dir, model_name=model)
print(f"\n完成！SRT: {srt_path}")

# 打印前几行看看效果
with open(srt_path, encoding="utf-8") as f:
    content = f.read()
lines = content.splitlines()[:15]
print("\n--- 前几条字幕 ---")
print("\n".join(lines))
