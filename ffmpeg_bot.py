import os
import subprocess
import random
import secrets
import string
from pathlib import Path

INPUT_DIR = "videos/incoming"
OUTPUT_DIR = "videos/ready"
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_video(input_path):
    filename = Path(input_path).stem
    random_name = generate_random_filename()
    output_path = os.path.join(OUTPUT_DIR, f"{random_name}.mp4")

    # Randomize crop slightly
    crop_percent = random.uniform(0.01, 0.03)
    crop_filter = f"crop=iw*{1 - crop_percent}:ih*{1 - crop_percent}"

    # Random brightness/saturation (within ±3%)
    brightness = round(random.uniform(-0.03, 0.03), 3)
    saturation = round(random.uniform(0.97, 1.03), 3)
    eq_filter = f"eq=brightness={brightness}:saturation={saturation}"

    # Random mirror flip (50% chance)
    #apply_mirror = random.choice([True, False])
    apply_mirror = False
    mirror_filter = "hflip" if apply_mirror else ""

    # Combine all filters
    filter_list = [crop_filter, eq_filter]
    if mirror_filter:
        filter_list.append(mirror_filter)
    full_filter = ",".join(filter_list)

    # Random speed adjustment (1–2% faster/slower)
    speed = round(random.uniform(0.98, 1.02), 2)
    atempo_values = []
    # 'atempo' only supports values between 0.5 and 2.0, but must be split if outside safe range
    while not 0.5 <= speed <= 2.0:
        val = 1.5 if speed > 1.5 else 0.75
        atempo_values.append(val)
        speed /= val
    atempo_values.append(round(speed, 2))
    atempo_filter = ",".join([f"atempo={v}" for v in atempo_values])

    bg_audio_path = "assets/audio/background.mp3"

    # Check if background audio exists
    if os.path.exists(bg_audio_path):
        command = [
            "ffmpeg",
            "-i", input_path,
            "-i", bg_audio_path,
            "-filter_complex",
            f"[0:a]atempo={speed}[a1];[1:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2",
            "-vf", full_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-map_metadata", "-1",
            "-metadata", "title=",
            "-metadata", "comment=",
            "-metadata", "artist=",
            "-metadata", "encoder=",
            output_path
        ]
    else:
        print("⚠️ Background audio file not found — skipping overlay.")
        command = [
            "ffmpeg",
            "-i", input_path,
            "-vf", full_filter,
            "-filter:a", atempo_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-map_metadata", "-1",
            "-metadata", "title=",
            "-metadata", "comment=",
            "-metadata", "artist=",
            "-metadata", "encoder=",
            output_path
        ]
    
    subprocess.run(command, check=True)
    if apply_mirror:
        print("🔁 Mirror flip applied.")
    else:
        print("➡️ No mirror flip this time.")
    print(f"🎧 Audio speed set to ~{speed}x with atempo: {atempo_filter}")
    print(f"📝 Original: {filename} → Output: {random_name}.mp4")
    print(f"✅ Processed and saved: {output_path}")

    # SSIM comparison with original input video as reference
    reference_video = input_path
    if os.path.exists(reference_video):
        ssim_output = f"{output_path}_ssim_log.txt"
        cmd = [
            "ffmpeg",
            "-i", reference_video,
            "-i", output_path,
            "-lavfi", f"[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2[ref];"
                      f"[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2[out];"
                      f"[ref][out]ssim=stats_file={ssim_output}",
            "-f", "null", "-"
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            with open(ssim_output, "r") as f:
                for line in reversed(f.readlines()):
                    if "All:" in line:
                        print(f"📊 SSIM Score: {line.strip()}")
                        break
        except Exception as e:
            print(f"⚠️ SSIM comparison failed: {e}")
    else:
        print("⚠️ No reference video found for SSIM comparison.")

def run_batch():
    for file in os.listdir(INPUT_DIR):
        if file.lower().endswith(".mp4") or file.lower().endswith(".mov"):
            full_path = os.path.join(INPUT_DIR, file)
            process_video(full_path)

def generate_random_filename(length=8):
    return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))


if __name__ == "__main__":
    print("🔄 Running batch re-encode...")
    run_batch()
