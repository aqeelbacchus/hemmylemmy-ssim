import os
import subprocess
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "7578704626:AAFnizj6o7Z5uPUkutGclqOigLQnqcT1QG0"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

pending_profile_requests = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send me TikTok links and I’ll send back HD downloads!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive and ready to download TikTok videos.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = (update.message.text or update.message.caption or "").strip()
    print(f"[DEBUG] RAW handle_link text: {repr(text)} from user {user_id}")

    # Try extracting links from the message text using regex
    links = re.findall(r'https?://(?:www\.)?tiktok\.com/[^\s]+', text)

    # Also scan entities if no links were found directly
    if not links and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "url":
                entity_text = text[entity.offset: entity.offset + entity.length]
                if "tiktok.com" in entity_text:
                    links.append(entity_text)

    print(f"[DEBUG] extracted links: {links}")

    if not links:
        await update.message.reply_text("❌ Please send one or more valid TikTok links.")
        return

    for link in links:
        if "/video/" in link:
            await process_video_link(update, link)
        elif "/@" in link:
            pending_profile_requests[user_id] = link
            await update.message.reply_text("🔢 How many recent videos would you like to download? (Max 10)")
        else:
            await update.message.reply_text(f"❌ Unsupported link format: {link}")

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Prevent non-numeric replies from interfering
    if not text.isdigit():
        return  # Ignore anything that's not a plain number

    print(f"[DEBUG] handle_response received: '{text}' from user {user_id}")
    print(f"[DEBUG] pending_profile_requests: {pending_profile_requests}")

    # Only respond if a profile request is pending
    if user_id not in pending_profile_requests:
        print("[DEBUG] Ignoring message: no pending profile request.")
        return

    try:
        count = min(10, max(1, int(text)))
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number between 1 and 10.")
        return

    profile_url = pending_profile_requests.pop(user_id)
    await update.message.reply_text(f"⏬ Downloading last {count} videos from: {profile_url}")

    output_path = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--playlist-end", str(count),
        "-o", output_path,
        "-f", "bv*+ba/best",
        "--merge-output-format", "mp4",
        "--no-warnings",
        "--quiet",
        profile_url
    ]

    try:
        existing_files = set(os.listdir(DOWNLOAD_DIR))
        subprocess.run(cmd, check=True, timeout=180)
        new_files = [f for f in os.listdir(DOWNLOAD_DIR) if f not in existing_files]
        if not new_files:
            await update.message.reply_text("❌ No new videos were found.")
        else:
            for file in sorted(new_files):
                new_file_path = os.path.join(DOWNLOAD_DIR, file)
                await update.message.reply_video(video=open(new_file_path, "rb"))
    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading videos: {e}")

async def process_video_link(update: Update, link: str):
    await update.message.reply_text(f"⏬ Downloading: {link}")

    output_path = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bv*+ba/best",
        "-o", output_path,
        "--no-warnings",
        "--quiet",
        "--merge-output-format", "mp4",
        link
    ]

    try:
        existing_files = set(os.listdir(DOWNLOAD_DIR))
        subprocess.run(cmd, check=True, timeout=180)
        new_files = [f for f in os.listdir(DOWNLOAD_DIR) if f not in existing_files]
        if new_files:
            new_file_path = os.path.join(DOWNLOAD_DIR, new_files[0])
            await update.message.reply_video(video=open(new_file_path, "rb"))
        else:
            await update.message.reply_text(f"❌ Could not find downloaded video for: {link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading {link}: {e}")

def main():
    print("Launching bot...")

    async def debug_logger(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("[DEBUG] debug_logger fallback triggered")
        print(f"[DEBUG] Full update.message object:\n{update.message}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.Regex(r"^\d+$"), handle_response))
    app.add_handler(MessageHandler(filters.Regex(r"tiktok\.com"), handle_link))
    app.add_handler(MessageHandler(filters.ALL, debug_logger))
    
    print("🎥 TikTok Downloader Bot is running...")
    try:
        app.run_polling()
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")

if __name__ == "__main__":
    main()