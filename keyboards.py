"""
N4X Bot — saare texts aur inline keyboards ek jagah.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config

# ---------------------------------------------------------------- keyboards


def _b(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data)


def main_menu(connected: bool) -> InlineKeyboardMarkup:
    if connected:
        rows = [
            [_b("📤 APK / File Upload", "upload")],
            [_b("📊 Status", "status"), _b("🗂 Recent", "list")],
            [_b("ℹ️ About", "about")],
            [_b("🔌 Disconnect", "disconnect")],
        ]
    else:
        rows = [
            [_b("🔗 Connect Channel", "connect")],
            [_b("ℹ️ About", "about")],
        ]
    return InlineKeyboardMarkup(rows)


def retry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_b("🔄 Retry (admin add karne ke baad)", "retry")],
        [_b("❌ Cancel", "cancel")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_b("❌ Cancel", "cancel")]])


def skipowner_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_b("⏭ Skip", "skipowner")],
        [_b("❌ Cancel", "cancel")],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_b("⏭ Skip description", "skipdesc")],
        [_b("❌ Cancel", "cancel")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_b("⬅️ Main menu", "menu")]])


def connect_required_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_b("🔗 Connect Channel", "connect")],
        [_b("ℹ️ About", "about")],
    ])


def confirm_disconnect_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_b("✅ Haan, disconnect", "disc_yes")],
        [_b("↩️ Nahi", "menu")],
    ])


# ---------------------------------------------------------------- texts


def start_text(connected: bool, row=None) -> str:
    if connected:
        ch = f"@{row['username']}" if row["username"] else f"<code>{row['chat_id']}</code>"
        return (
            f"🤖 <b>{config.BOT_NAME}</b> — ready hai\n\n"
            f"📢 Connected channel: <b>{_e(row['title'])}</b> ({ch})\n"
            f"👤 Owner: <b>{_e(row['owner_name'])}</b>\n\n"
            "<b>Upload karne ke liye</b>\n"
            "• <code>/apk add</code> — file bhejiye (APK / ZIP / PDF / TXT)\n"
            "• Phir description likhiye — post seedha channel me chala jayega\n\n"
            "Ya neeche <b>APK / File Upload</b> dabaiye."
        )
    return (
        f"🤖 <b>{config.BOT_NAME}</b> — Telegram Channel Upload Bot\n\n"
        "Is bot se aap apne channel me seedha <b>APK, ZIP, PDF, TXT</b> aur baaki "
        "files upload kar sakte hain — phone ki file manager se, description ke saath.\n\n"
        "<b>Kaam kaise karega</b>\n"
        "1️⃣ <b>Connect</b> — channel username, owner ka naam, admin ka mobile number\n"
        "2️⃣ Bot ko channel me <b>Admin</b> banaiye (Post messages ✅)\n"
        "3️⃣ <code>/apk add</code> — file + description → channel me post\n\n"
        "Shuru karne ke liye neeche <b>Connect Channel</b> dabaiye — "
        "ya seedha channel ka <code>@username</code> bhej dijiye.\n\n"
        f"👑 Owner: <b>{config.OWNER_NAME}</b>\n"
        f"📸 Instagram: @{config.OWNER_INSTAGRAM}\n"
        f"✈️ Telegram: @{config.OWNER_TELEGRAM}"
    )


def connect_step1(bot_username: str = "") -> str:
    bot = f"@{bot_username}" if bot_username else "apna bot"
    return (
        "🔗 <b>Channel Connect — Step 1 of 3</b>\n\n"
        f"<b>Pehle ye kariye:</b> channel → Administrators → Add Admin → {bot}\n"
        "→ <b>Post messages</b> ✅ on kariye.\n\n"
        "Ab me se koi ek bhejiye:\n"
        "• <code>@mychannel</code> — public channel ka username\n"
        "• <code>https://t.me/mychannel</code> — channel link\n"
        "• <code>-1001234567890</code> — private channel ki ID\n"
        "• <b>ya channel ki koi post yahan forward kar dijiye</b> "
        "(private channel ke liye sabse aasan)\n\n"
        "⚠️ Channel ka <i>display name</i> (jaise \"My Movies\") likhne se channel nahi milega — "
        "username ya forward chahiye."
    )


def connect_step2(chat_title: str) -> str:
    return (
        f"✅ Channel mil gaya: <b>{_e(chat_title)}</b>\n\n"
        "🔗 <b>Step 2 of 3</b>\n\n"
        "Ab channel ke <b>owner ka naam</b> bhejiye."
    )


def connect_step3(owner_name: str) -> str:
    return (
        f"✅ Owner name saved: <b>{_e(owner_name)}</b>\n\n"
        "🔗 <b>Step 3 of 3</b>\n\n"
        "Ab channel ke <b>admin ka real mobile number</b> bhejiye.\n"
        "Format: <code>+91XXXXXXXXXX</code> ya <code>10-digit number</code>\n\n"
        "<i>Note: Telegram Bot API se mobile number verify nahi hota. Yeh number "
        "sirf aapke admin record ke liye save hota hai — asli verification "
        "Telegram ke channel admin rights se hoti hai.</i>"
    )


def connected_text(row) -> str:
    ch = f"@{row['username']}" if row["username"] else f"<code>{row['chat_id']}</code>"
    link = f"https://t.me/{row['username']}" if row["username"] else "private channel"
    return (
        "🎉 <b>Channel connect ho gaya!</b>\n\n"
        f"📢 Channel: <b>{_e(row['title'])}</b>\n"
        f"🔗 Link: {link}\n"
        f"🆔 {ch}\n"
        f"👤 Owner: <b>{_e(row['owner_name'])}</b>\n"
        f"📱 Admin phone: <code>{_e(row['admin_phone'])}</code>\n\n"
        "<b>Ab upload kariye</b>\n"
        "<code>/apk add</code> → file bhejiye → description likhiye → channel me post ✅"
    )


def upload_prompt(row) -> str:
    ch = f"@{row['username']}" if row["username"] else f"<code>{row['chat_id']}</code>"
    allowed = "  ·  ".join(sorted({e.upper().lstrip('.') for e in config.ALLOWED_EXTENSIONS}))
    return (
        f"📤 <b>Upload to {_e(row['title'])}</b> ({ch})\n\n"
        "Ab <b>file bhejiye</b> — document/attachment ke roop me.\n\n"
        f"✅ Allowed: {allowed}\n"
        f"📦 Max size: {config.MAX_FILE_MB} MB\n\n"
        "File ke saath caption bhi likh sakte hain — wo hi description ban jayega.\n"
        "Nahi likha to next step me poocha jayega."
    )


def about_text() -> str:
    return (
        f"🤖 <b>{config.BOT_NAME}</b> — Telegram Channel Upload Bot\n\n"
        "Channel me APK, ZIP, PDF, TXT aur baaki files seedha upload karne ke liye "
        "banaya gaya hai — bina kisi doosre app ke.\n\n"
        "<b>Features</b>\n"
        "• Channel connect — username + owner + admin number\n"
        "• Bot admin verification (Telegram ke asli admin rights se)\n"
        "• <code>/apk add</code> se file + description upload\n"
        "• Upload history, status aur disconnect\n\n"
        "<b>Banane wala</b>\n"
        f"👑 Name: <b>{config.OWNER_NAME}</b>\n"
        f"📸 Instagram: @{config.OWNER_INSTAGRAM}\n"
        f"✈️ Telegram: @{config.OWNER_TELEGRAM}"
    )


HELP_TEXT = (
    "<b>Commands</b>\n"
    "/start — main menu\n"
    "/apk add — file upload kariye (APK / ZIP / PDF / TXT)\n"
    "/connect — channel connect kariye\n"
    "/status — channel + upload count\n"
    "/list — last 10 uploads\n"
    "/disconnect — channel remove kariye\n"
    "/cancel — current step cancel\n"
    "/about — bot aur owner ki details\n"
    "/help — yeh message\n\n"
    "<b>Zaroori</b>: bot ko channel me Admin banana padta hai "
    "(Post messages permission)."
)

ALREADY_CONNECTED = (
    "ℹ️ Aapka ek channel pehle se connected hai.\n\n"
    "Doosra channel jodne ke liye pehle <b>Disconnect</b> kariye."
)

NOT_ADMIN = (
    "❌ Aap is channel ke <b>admin nahi</b> hain.\n\n"
    "Telegram sirf channel admins ko hi bot se post karne deta hai. "
    "Channel owner se apne aap ko admin banwaiye, phir dobara try kariye."
)

STRAY_DOC = (
    "📎 File mil gayi, par pehle upload shuru karna hoga.\n\n"
    "<code>/apk add</code> bhejiye, phir file bhejiye."
)


def _e(value) -> str:
    """HTML escape."""
    import html
    return html.escape(str(value if value is not None else ""))
