# 🚀 Mega to GoFile Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-green)](https://core.telegram.org/bots)
[![Render](https://img.shields.io/badge/Deploy-Render-43E047?logo=render)](https://render.com)

A Telegram bot that converts Mega.nz file links to GoFile.io links without requiring any logins. Includes a secure admin panel for monitoring and management.

## ✨ Features

- **No Login Required**: Converts Mega.nz links to GoFile.io without credentials
- **Admin Panel**: Secure web interface for monitoring and management
- **Real-time Statistics**: Track conversions, success rates, and activity
- **Admin Management**: Add/remove admins via Telegram or web panel
- **User-Friendly**: Clean interface with progress indicators
- **Deploy Anywhere**: Optimized for Render.com deployment
- **Secure**: Password-protected admin panel with rate limiting

## 📦 Requirements

- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Your Telegram User ID (from [@userinfobot](https://t.me/userinfobot))
- [Render.com](https://render.com) account (free tier works)

## 🚀 Deployment on Render.com

### 1. Create GitHub Repository

1. Fork or create a new repository with the [project files](https://github.com/yourusername/mega-gofile-bot)
2. Push all project files to your repository

### 2. Deploy Web Service (Admin Panel)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/web)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `mega-gofile-web`
   - **Region**: Select closest to your location
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT web:app`
5. Add Environment Variables:
   ```
   ADMIN_PANEL_PASSWORD=your_secure_password_here
   ```
6. Click **Create Web Service**

### 3. Deploy Worker Service (Telegram Bot)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/web)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Worker**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `mega-gofile-worker`
   - **Region**: Same as web service
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python worker.py`
5. Add Environment Variables:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   INITIAL_ADMIN=your_telegram_user_id
   ADMIN_PANEL_URL=https://mega-gofile-web.onrender.com
   DOCUMENT_AS_FILE=True
   USE_THUMBNAIL=True
   ```
6. Click **Create Worker**

> **Note**: Replace `your_secure_password_here`, `your_telegram_bot_token`, and `your_telegram_user_id` with your actual values.

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `INITIAL_ADMIN` | Your Telegram user ID | `123456789` |
| `ADMIN_PANEL_PASSWORD` | Password for admin panel | `secure_password123` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_PANEL_URL` | URL of web service | `https://mega-gofile-web.onrender.com` |
| `DOCUMENT_AS_FILE` | Send as document instead of media | `True` |
| `USE_THUMBNAIL` | Use thumbnails for media | `True` |

## 🖥️ Using the Admin Panel

1. After deployment, access your admin panel at:
   ```
   https://mega-gofile-web.onrender.com/login
   ```
2. Login with the password you set for `ADMIN_PANEL_PASSWORD`
3. Dashboard includes:
   - Real-time conversion statistics
   - Success/failure rates
   - Hourly activity charts
   - Admin management interface

![Admin Panel Screenshot](https://i.imgur.com/7XbRk9L.png)

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message |
| `/gofile [link]` | Convert Mega.nz link to GoFile.io |
| `/admin add [id]` | Add new admin |
| `/admin remove [id]` | Remove admin |
| `/admin list` | View all admins |

### Example Usage
```
/gofile https://mega.nz/file/mhJyxLxS#kTpYLbOMIxzLYUGedovrzL1ds3hJhIuDtr3XsLFd5F8
```

## 🔒 Security Notes

1. The admin panel is password-protected with rate limiting
2. Only configured admins can use the bot
3. Admin panel is only accessible via HTTPS
4. For production use:
   - Use a strong, unique password
   - Consider adding IP restrictions
   - Monitor activity in the admin panel

## 🌐 How It Works

1. User sends a Mega.nz link to the bot
2. Bot downloads the file from Mega.nz (no login required)
3. Bot uploads the file to GoFile.io (no login required)
4. Bot returns GoFile.io download links to the user
5. All activity is tracked in the admin panel

## 📈 Statistics Tracked

- Total conversions
- Successful conversions
- Failed conversions
- Bot uptime
- Active users
- Hourly conversion rates

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 💬 Support

For help with deployment or issues:

1. Check the [Render.com documentation](https://render.com/docs)
2. Open an issue in the GitHub repository
3. Join our [Telegram Support Group](https://t.me/your_support_group)

---

> **Note**: This bot uses third-party services (Mega.nz and GoFile.io) under their respective terms of service. The developer is not responsible for any content shared through this bot.

**Happy Converting!** 🚀
