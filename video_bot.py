import os
import random
import moviepy.editor as mpy
from moviepy.video.fx.all import crop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INPUT_DIR = "videos/incoming"
OUTPUT_DIR = "videos/ready"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def transform_video(path):
    filename = os.path.basename(path)
    base, ext = os.path.splitext(filename)
    if ext.lower() != ".mp4":
        return

    output_path = os.path.join(OUTPUT_DIR, f"{base}_modified.mp4")

    clip = mpy.VideoFileClip(path)
    width, height = clip.size

    # Apply a random slight crop
    crop_percent = random.uniform(0.01, 0.03)
    crop_w = int(width * crop_percent)
    crop_h = int(height * crop_percent)

    clip = crop(clip, x1=crop_w, y1=crop_h, x2=crop_w, y2=crop_h)
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"Processed: {output_path}")

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".mp4"):
            print(f"Detected new file: {event.src_path}")
            transform_video(event.src_path)

if __name__ == "__main__":
    print("📁 Watching for new MP4 files...")
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, path=INPUT_DIR, recursive=False)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
