"""
N4X Bot — configuration file.
Yahin par token aur owner details set hote hain.
"""

import os

# ---------------------------------------------------------------- bot identity
BOT_NAME = "N4X"

# BotFather se mila hua token yahan daaliye, ya environment variable use kariye:
#   export BOT_TOKEN="123456:ABC..."
BOT_TOKEN = os.getenv("BOT_TOKEN", "9279461220:AAFiniwFASDkGWOUW0fVEmV2ax5_0IRS7Hg")

# ---------------------------------------------------------------- owner / about
OWNER_NAME = "Hari Jadhav"
OWNER_INSTAGRAM = "ur_.krishn._02"
OWNER_TELEGRAM = "nullkrishn"

# ---------------------------------------------------------------- storage
DB_PATH = os.getenv("N4X_DB", "n4x_bot.db")

# ---------------------------------------------------------------- limits
# Telegram Bot API ka normal upload limit 50 MB hai.
# (Local Bot API server use karein to 2000 MB tak ja sakta hai.)
MAX_FILE_MB = 50

# Kaun-kaun si files allowed hain
ALLOWED_EXTENSIONS = {
    ".apk", ".apks", ".xapk",      # Android apps
    ".zip", ".rar", ".7z",         # archives
    ".pdf", ".txt",                # documents
    ".csv", ".json", ".xml",       # data
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}

# File type ka label (caption me dikhta hai)
TYPE_LABELS = {
    ".apk": "APK",
    ".apks": "APKS",
    ".xapk": "XAPK",
    ".zip": "ZIP",
    ".rar": "RAR",
    ".7z": "7Z",
    ".pdf": "PDF",
    ".txt": "TXT",
}

# Caption ke neeche branding
BRAND_FOOTER = f'🤖 Uploaded via <b>{BOT_NAME}</b> · @{OWNER_TELEGRAM}'

# Telegram caption limit 1024 characters hai
CAPTION_LIMIT = 1000
