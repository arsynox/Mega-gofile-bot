import os
import re
import tempfile
import requests
import time
import threading
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ParseMode

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_FILE = "admins.txt"
STATS_FILE = "bot_stats.json"
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "http://localhost:5000")
DOCUMENT_AS_FILE = os.getenv("DOCUMENT_AS_FILE", "True").lower() == "true"
USE_THUMBNAIL = os.getenv("USE_THUMBNAIL", "True").lower() == "true"

# Global variables
admin_ids = []
stats_lock = threading.Lock()

def load_admins():
    """Load admin IDs from file"""
    global admin_ids
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, 'r') as f:
                admin_ids = [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        print(f"Error loading admins: {str(e)}")

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in admin_ids

def admin_only(func):
    """Decorator to restrict access to admins"""
    def wrapper(update: Update, context: CallbackContext):
        if not is_admin(update.effective_user.id):
            update.message.reply_text(
                "❌ You are not authorized to use this bot.\n"
                "Contact the bot owner to request access.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return func(update, context)
    return wrapper

def update_stats(success=True):
    """Update bot statistics via admin panel API"""
    try:
        response = requests.post(
            f"{ADMIN_PANEL_URL}/stats",
            json={"success": success},
            timeout=5
        )
        if response.status_code != 200:
            print(f"Failed to update stats: {response.text}")
    except Exception as e:
        print(f"Error updating stats: {str(e)}")

def decrypt_key(enc_key, shared_key):
    """Decrypt Mega key using shared key"""
    key = shared_key[:16]
    iv = shared_key[16:32]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(enc_key)
    return unpad(decrypted, AES.block_size)

def mega_download_url(url, output_path):
    """Download file from Mega.nz without mega.py dependency"""
    # Extract file ID and key from URL
    match = re.search(r'mega\.(nz|co)/file/([a-zA-Z0-9]+)#([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError("Invalid Mega URL format")
    
    file_id = match.group(2)
    key_str = match.group(3)
    
    # Parse the key string
    parts = key_str.split('!')
    if len(parts) < 2:
        raise ValueError("Invalid Mega key format")
    
    file_key = parts[0]
    shared_key = parts[1] if len(parts) > 1 else ""
    
    # Convert keys to bytes
    file_key_bytes = base64.urlsafe_b64decode(file_key + '==')
    shared_key_bytes = base64.urlsafe_b64decode(shared_key + '==') if shared_key else b''
    
    # Get file attributes
    api_url = f"https://g.api.mega.co.nz/cs?id=1&n={file_id}"
    payload = [{
        "a": "g",
        "g": "1",
        "p": file_id
    }]
    
    response = requests.post(api_url, data=json.dumps(payload))
    response.raise_for_status()
    
    data = response.json()[0]
    if "g" not in data:
        raise Exception(f"Failed to get download URL: {data}")
    
    download_url = data["g"]
    file_size = data["s"]
    
    # Download the file
    print(f"Downloading {file_size} bytes from {download_url}...")
    
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    return output_path

@admin_only
def convert_mega_to_gofile(update: Update, context: CallbackContext):
    """Converts Mega.nz link to GoFile.io link"""
    message = update.message
    user_id = update.effective_user.id
    
    mega_url = ' '.join(context.args).strip() if context.args else None
    
    if not mega_url:
        message.reply_text(
            "❌ Please provide a Mega.nz link after the command\n\n"
            "Example:\n`/gofile https://mega.nz/file/...`", 
            parse_mode=ParseMode.MARKDOWN
        )
        update_stats(success=False)
        return
    
    # Validate Mega URL format
    if not re.match(r'^https://mega\.(nz|co)/file/[a-zA-Z0-9]+#[a-zA-Z0-9_-]+$', mega_url):
        message.reply_text(
            "❌ Invalid Mega.nz link format\n\n"
            "Must be:\n`https://mega.nz/file/...#...`", 
            parse_mode=ParseMode.MARKDOWN
        )
        update_stats(success=False)
        return

    # Send initial processing message
    status_msg = message.reply_text(
        "🔄 Processing your request...\n\n"
        "1️⃣ Downloading from Mega.nz", 
        disable_notification=True
    )

    try:
        # Step 1: Download from Mega.nz (no login required)
        status_msg.edit_text(
            "🔄 Processing your request...\n\n"
            "1️⃣ Downloading from Mega.nz ✅\n"
            "2️⃣ Uploading to GoFile.io"
        )
        
        # Download to temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract filename from URL for proper saving
            filename = f"file_{int(time.time())}"
            file_path = os.path.join(tmpdir, filename)
            
            # Download the file
            mega_download_url(mega_url, file_path)
            
            # Step 2: Upload to GoFile.io (no login required)
            status_msg.edit_text(
                "🔄 Processing your request...\n\n"
                "1️⃣ Downloading from Mega.nz ✅\n"
                "2️⃣ Uploading to GoFile.io ⏳"
            )
            
            # Get upload server
            server_resp = requests.get('https://api.gofile.io/servers', timeout=10)
            server_resp.raise_for_status()
            server = server_resp.json()['data']['servers'][0]['name']
            
            # Upload file
            upload_url = f'https://{server}.gofile.io/uploadFile'
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                gofile_resp = requests.post(upload_url, files=files, timeout=60)
                gofile_resp.raise_for_status()
            
            # Parse response
            data = gofile_resp.json()
            if data.get('status') != 'ok':
                raise Exception(f"GoFile upload failed: {data.get('message', 'Unknown error')}")
            
            download_page = data['data']['downloadPage']
            content_url = data['data']['code']
            
            # Step 3: Send results to user
            result_text = (
                "✅ Conversion successful!\n\n"
                f"📥 Download from GoFile: [Link]({download_page})\n"
                f"🔗 Direct Content URL: [Link](https://gofile.io/d/{content_url})\n\n"
                "⚠️ *Note:* Links expire after 60 days of inactivity"
            )
            
            status_msg.edit_text(
                result_text, 
                parse_mode=ParseMode.MARKDOWN, 
                disable_web_page_preview=True
            )
            
            # Update statistics
            update_stats(success=True)
            
    except Exception as e:
        error_msg = f"❌ Operation failed:\n\n`{str(e)}`"
        status_msg.edit_text(error_msg, parse_mode=ParseMode.MARKDOWN)
        update_stats(success=False)

@admin_only
def start(update: Update, context: CallbackContext):
    """Send welcome message"""
    update.message.reply_text(
        "🚀 *Mega to GoFile Converter*\n\n"
        "Send me a Mega.nz file link with `/gofile` command and I'll convert it to GoFile.io link!\n\n"
        "✨ *Features:*\n"
        "• No login required\n"
        "• Automatic file conversion\n"
        "• Direct download links\n\n"
        "📌 *Example:*\n"
        "`/gofile https://mega.nz/file/mhJyxLxS#kTpYLbOMIxzLYUGedovrzL1ds3hJhIuDtr3XsLFd5F8`",
        parse_mode=ParseMode.MARKDOWN
    )

@admin_only
def admin_command(update: Update, context: CallbackContext):
    """Admin management command"""
    message = update.message
    args = context.args
    
    if not args:
        message.reply_text(
            "❌ Usage:\n"
            "`/admin add <user_id>` - Add new admin\n"
            "`/admin remove <user_id>` - Remove admin\n"
            "`/admin list` - Show all admins",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    subcommand = args[0].lower()
    
    if subcommand == "add":
        if len(args) < 2:
            message.reply_text("❌ Please provide a user ID to add")
            return
            
        try:
            new_admin_id = int(args[1])
        except ValueError:
            message.reply_text("❌ Invalid user ID. Must be a number")
            return
            
        if new_admin_id in admin_ids:
            message.reply_text(f"⚠️ User `{new_admin_id}` is already an admin", parse_mode=ParseMode.MARKDOWN)
            return
            
        # Send request to admin panel to add admin
        try:
            response = requests.post(
                f"{ADMIN_PANEL_URL}/add_admin",
                data={"admin_id": new_admin_id},
                timeout=5
            )
            result = response.json()
            if result.get("success"):
                load_admins()  # Refresh admin list
                message.reply_text(f"✅ Added `{new_admin_id}` as admin", parse_mode=ParseMode.MARKDOWN)
            else:
                message.reply_text(f"❌ Failed to add admin: {result.get('error', 'Unknown error')}")
        except Exception as e:
            message.reply_text(f"❌ Error adding admin: {str(e)}")
        
    elif subcommand == "remove":
        if len(args) < 2:
            message.reply_text("❌ Please provide a user ID to remove")
            return
            
        try:
            remove_id = int(args[1])
        except ValueError:
            message.reply_text("❌ Invalid user ID. Must be a number")
            return
            
        if remove_id not in admin_ids:
            message.reply_text(f"⚠️ User `{remove_id}` is not an admin", parse_mode=ParseMode.MARKDOWN)
            return
            
        # Send request to admin panel to remove admin
        try:
            response = requests.post(
                f"{ADMIN_PANEL_URL}/remove_admin",
                data={"admin_id": remove_id},
                timeout=5
            )
            result = response.json()
            if result.get("success"):
                load_admins()  # Refresh admin list
                message.reply_text(f"✅ Removed `{remove_id}` from admins", parse_mode=ParseMode.MARKDOWN)
            else:
                message.reply_text(f"❌ Failed to remove admin: {result.get('error', 'Unknown error')}")
        except Exception as e:
            message.reply_text(f"❌ Error removing admin: {str(e)}")
        
    elif subcommand == "list":
        if not admin_ids:
            message.reply_text("📭 No admins configured")
            return
            
        admin_list = "\n".join([f"• `{admin_id}`" for admin_id in admin_ids])
        message.reply_text(
            f"📋 *Current Admins:*\n{admin_list}\n\n"
            "Use `/admin add <user_id>` to add new admins",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        message.reply_text(
            "❌ Unknown subcommand. Use:\n"
            "`add`, `remove`, or `list`",
            parse_mode=ParseMode.MARKDOWN
        )

def setup_initial_admin():
    """Set up initial admin if no admins exist"""
    global admin_ids
    
    # Check if admins file exists
    if not os.path.exists(ADMIN_FILE) and 'INITIAL_ADMIN' in os.environ:
        try:
            initial_admin = int(os.environ['INITIAL_ADMIN'])
            # Send request to admin panel to add admin
            response = requests.post(
                f"{ADMIN_PANEL_URL}/add_admin",
                data={"admin_id": initial_admin},
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Created initial admin: {initial_admin}")
            else:
                print(f"❌ Failed to create initial admin: {response.text}")
        except Exception as e:
            print(f"❌ Error setting up initial admin: {str(e)}")

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Load admin configuration
    load_admins()
    setup_initial_admin()
    
    if not admin_ids:
        raise RuntimeError("No admins configured. Set INITIAL_ADMIN environment variable")

    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gofile", convert_mega_to_gofile))
    dp.add_handler(CommandHandler("admin", admin_command))
    
    # Fallback for unknown commands (only for admins)
    dp.add_handler(MessageHandler(
        Filters.command & ~Filters.update.edited_message, 
        lambda update, context: update.message.reply_text(
            "❌ Unknown command. Use /start for help",
            parse_mode=ParseMode.MARKDOWN
        )
    ))

    # Start the Bot
    updater.start_polling()
    print(f"✅ Bot running with {len(admin_ids)} admins")
    print(f"   Admin IDs: {', '.join(map(str, admin_ids))}")
    updater.idle()

if __name__ == '__main__':
    # Wait for web service to start
    time.sleep(5)
    main()
