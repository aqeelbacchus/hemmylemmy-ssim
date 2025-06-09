import os
import subprocess
import asyncio
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
video_storage = {}

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready to compare videos.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📹 Send me *two* videos, and I’ll return the SSIM score comparing them.", parse_mode="Markdown")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_dir = f"temp/{user_id}"
    os.makedirs(user_dir, exist_ok=True)

    video_file = update.message.video or update.message.document
    if not video_file:
        await update.message.reply_text("❌ Please send an actual video file.")
        return

    file = await context.bot.get_file(video_file.file_id)
    filepath = os.path.join(user_dir, f"{video_file.file_unique_id}.mp4")
    await file.download_to_drive(custom_path=filepath)

    video_storage.setdefault(user_id, []).append(filepath)

    if len(video_storage[user_id]) < 2:
        await update.message.reply_text("✅ First video received. Now send me the second one.")
    else:
        v1, v2 = video_storage[user_id][:2]
        await update.message.reply_text("🔍 Comparing videos now...")

        ssim_log = os.path.join(user_dir, "ssim_log.txt")
        cmd = [
            "ffmpeg", "-i", v1, "-i", v2,
            "-lavfi", f"[0:v]scale=w=720:h=1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black[v0];"
                      f"[1:v]scale=w=720:h=1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black[v1];"
                      f"[v0][v1]ssim=stats_file={ssim_log}",
            "-f", "null", "-"
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            with open(ssim_log) as f:
                score_line = next((line for line in reversed(f.readlines()) if "All:" in line), "SSIM score not found.")
            import re
            match = re.search(r'All:([\d.]+)', score_line)
            ssim_value = float(match.group(1)) if match else None
            if ssim_value is not None:
                rating = ""
                if ssim_value >= 0.95:
                    rating = "🔁 Almost identical"
                elif ssim_value >= 0.85:
                    rating = "🟢 Very similar"
                elif ssim_value >= 0.70:
                    rating = "🟡 Moderately different"
                else:
                    rating = "🔴 Significantly different"
                await update.message.reply_text(f"📊 SSIM score: {ssim_value:.2f} — {rating}")
            else:
                await update.message.reply_text("⚠️ SSIM score not found in output.")
            
            # Clean up files
            try:
                os.remove(v1)
                os.remove(v2)
                os.remove(ssim_log)
            except Exception:
                pass
        except Exception as e:
            await update.message.reply_text(f"❌ Error comparing videos: {e}")

        # Clean up
        video_storage[user_id] = []

if __name__ == "__main__":
    print("Launching bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    print("🤖 Bot is running...")
    app.run_polling()