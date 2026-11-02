"""
N4X Bot — saare handlers (connect flow, upload flow, commands).

Flow 1 — Connect:
    /connect → channel username → owner ka naam → admin ka mobile number
              → Telegram se admin verification → DB me save

Flow 2 — Upload:
    /apk add → file (APK/ZIP/PDF/TXT) → description → channel me post
"""

import html
import logging
import os
import re
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import keyboards as ui

log = logging.getLogger(__name__)

# Conversation states (numbers must not overlap between conversations)
(CONNECT_CHANNEL, CONNECT_OWNER, CONNECT_PHONE, UPLOAD_FILE, UPLOAD_DESC) = range(5)

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{7,17}$")

# Channel ka reference: @name, name, t.me/name, t.me/name/123, -1001234567890
CHANNEL_REF_RE = re.compile(
    r"^(?:https?://)?(?:t\.me/|telegram\.me/|telegram\.dog/)?"
    r"(?:@?[A-Za-z_][A-Za-z0-9_]{3,63}|-?100\d{6,13}|-?\d{12,20})(?:/\d+)?/?$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- helpers


def db(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["db"]


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


async def _reply(update: Update, text: str, kb=None) -> None:
    """Callback se aaya to purana message edit karo, warna naya bhejo."""
    kwargs = dict(parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=kb, **kwargs)
            return
        except TelegramError:
            pass  # "message is not modified" ya purana message — naya bhej denge
        await query.message.reply_text(text, reply_markup=kb, **kwargs)
        return
    await update.effective_message.reply_text(text, reply_markup=kb, **kwargs)


async def resolve_channel(bot, raw: str):
    """@username / t.me link / -100... ID — sabko chat object me badalta hai."""
    ref = (raw or "").strip()
    ref = re.sub(r"^https?://", "", ref, flags=re.IGNORECASE).strip()
    if ref.lower().startswith("t.me/"):
        ref = ref[5:]
    ref = ref.split("?")[0].strip().strip("/")
    if not ref:
        raise TelegramError("empty channel reference")
    if ref.startswith("+") or ref.lower().startswith("joinchat/"):
        ref = "https://t.me/" + ref
    else:
        ref = ref.split("/")[0].strip()   # t.me/name/123 → name
        if not ref:
            raise TelegramError("empty channel reference")
        if not ref.startswith("-") and not ref.startswith("@"):
            ref = "@" + ref
    return await bot.get_chat(ref)


def channel_ref_from_message(message):
    """Forwarded post se channel ka chat id nikalta hai (warna None)."""
    if message is None:
        return None
    origin = getattr(message, "forward_origin", None)
    if origin is None:
        return None
    chat = getattr(origin, "chat", None)
    if chat is not None and getattr(chat, "type", "") == "channel":
        return chat.id
    sender_chat = getattr(origin, "sender_chat", None)
    if sender_chat is not None and getattr(sender_chat, "type", "") == "channel":
        return sender_chat.id
    return None


class IsChannelForward(filters.MessageFilter):
    """Filter: message kisi channel se forward hua hai."""

    def filter(self, message) -> bool:
        return channel_ref_from_message(message) is not None


def looks_like_channel_ref(text: str) -> bool:
    return bool(text) and bool(CHANNEL_REF_RE.match(text.strip()))


async def bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        me = await context.bot.get_me()
        return me.username or ""
    except TelegramError:
        return ""


# Telegram ke technical errors ko aam bhasha me
ACCESS_HINTS = {
    "member list is inaccessible": "bot is channel me admin nahi hai (channel me add hi nahi hua)",
    "chat not found": "bot is channel me nahi hai, ya channel private hai",
    "user not found": "bot is channel ka member nahi hai",
    "not enough rights": "bot ke paas ye permission nahi hai",
    "bot is not a member": "bot channel me member nahi hai",
}


def explain_access_error(exc) -> str:
    text = str(exc).lower()
    for key, hint in ACCESS_HINTS.items():
        if key in text:
            return hint
    return str(exc)


async def bot_can_post(bot, chat_id: int):
    """Bot channel me admin hai aur post kar sakta hai?"""
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
    except TelegramError as exc:
        return False, explain_access_error(exc)

    status = getattr(member, "status", "")
    if status == "creator":
        return True, "ok"
    if status == "administrator":
        if getattr(member, "can_post_messages", True) is False:
            return False, "admin hai par 'Post messages' permission off hai"
        return True, "ok"
    return False, f"bot channel me admin nahi hai (status: {status})"


async def is_channel_admin(bot, chat_id: int, user_id: int) -> bool:
    """Yeh user us channel ka asli Telegram admin hai ya nahi."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except TelegramError:
        return False
    return any(a.user.id == user_id for a in admins)


def build_caption(title: str, description: str, info: dict, user) -> str:
    label = config.TYPE_LABELS.get(info["ext"], info["ext"].lstrip(".").upper() or "FILE")
    size_mb = (info["size"] or 0) / (1024 * 1024)
    stamp = datetime.now().astimezone().strftime("%d/%m/%Y %I:%M %p")
    head = f"<b>{_esc(title)}</b>"
    body = description.strip() if description else ""
    if len(body) > 600:
        body = body[:597] + "..."
    parts = [head]
    if body:
        parts.append(_esc(body))
    parts.append(
        f"📦 File: <code>{_esc(info['name'])}</code>\n"
        f"🗂 Type: {label} · {size_mb:.1f} MB\n"
        f"👤 By: {_esc(user.full_name)}\n"
        f"🕒 {stamp}"
    )
    parts.append(config.BRAND_FOOTER)
    caption = "\n\n".join(parts)
    return caption[: config.CAPTION_LIMIT]


# ---------------------------------------------------------------- /start, /help, /about


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db(context).touch_user(user.id, user.username, user.full_name)
    row = db(context).channel_of(user.id)
    await update.message.reply_text(
        ui.start_text(bool(row), row),
        reply_markup=ui.main_menu(bool(row)),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, ui.HELP_TEXT, ui.main_menu(bool(db(context).channel_of(update.effective_user.id))))


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    await _reply(update, ui.about_text(), ui.back_kb())


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    row = db(context).channel_of(update.effective_user.id)
    await _reply(update, ui.start_text(bool(row), row), ui.main_menu(bool(row)))


async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot ki channel access ka poora check — kuch na chale to yeh bhejiye."""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    me = await context.bot.get_me()
    row = db(context).channel_of(user.id)

    lines = [
        "🔍 <b>Diagnostics</b>\n",
        f"Bot: @{_esc(me.username)}",
        f"Aapka user ID: <code>{user.id}</code>",
    ]
    if not row:
        lines.append("Channel: ❌ connect nahi hai — <code>/connect</code> bhejiye")
    else:
        ok, reason = await bot_can_post(context.bot, row["chat_id"])
        admin = await is_channel_admin(context.bot, row["chat_id"], user.id)
        try:
            admins = len(await context.bot.get_chat_administrators(row["chat_id"]))
        except TelegramError:
            admins = -1
        lines += [
            f"Channel: {_esc(row['title'])} (<code>{row['chat_id']}</code>)",
            f"Bot post kar sakta hai: {'✅' if ok else '❌ ' + _esc(reason)}",
            f"Aap admin hain: {'✅' if admin else '❌'}",
            f"Channel admins: {admins}",
        ]
    await _reply(update, "\n".join(lines), ui.main_menu(bool(row)))


# ---------------------------------------------------------------- connect conversation


async def connect_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    db(context).touch_user(user.id, user.username, user.full_name)

    existing = db(context).channel_of(user.id)
    if existing:
        await _reply(update, ui.ALREADY_CONNECTED, ui.main_menu(True))
        return ConversationHandler.END

    context.user_data.pop("connect", None)
    context.user_data["connect"] = {}

    # Ek hi line me connect: /connect @channel [owner naam] [mobile number]
    args = list(context.args or [])
    if args:
        return await _connect_from_args(update, context, args)

    await _reply(
        update, ui.connect_step1(await bot_username(context)), ui.cancel_kb()
    )
    return CONNECT_CHANNEL


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if (raw or "").strip().startswith("+"):
        return "+" + digits
    return f"+91{digits[-10:]}"


async def _connect_from_args(
    update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
) -> int:
    """`/connect @channel Owner Name 9876543210` — bina step-by-step."""
    ref = args[0]
    rest = args[1:]
    phone = None
    name = " ".join(rest).strip() or None

    if rest and len(re.sub(r"\D", "", rest[-1])) >= 10:
        phone = _normalize_phone(rest[-1])
        name = " ".join(rest[:-1]).strip() or None

    chat = await _process_channel_input(update, context, ref)
    if chat is None:
        return CONNECT_CHANNEL

    data = {"chat_id": chat.id, "username": chat.username, "title": chat.title}
    if name:
        data["owner_name"] = name
    context.user_data["connect"] = data

    if phone:
        data["owner_name"] = name or chat.title
        return await _finalize_connect(update, context, data, phone)

    await update.effective_message.reply_text(
        ui.connect_step2(chat.title),
        parse_mode=ParseMode.HTML,
        reply_markup=ui.skipowner_kb(),
    )
    return CONNECT_OWNER  # owner step


async def _process_channel_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, ref: str = ""
):
    """Channel resolve + type check + bot permission check. Chat object ya None."""
    message = update.effective_message
    forwarded_id = channel_ref_from_message(message)

    # Retry button ke liye yaad rakho
    if forwarded_id:
        context.user_data["last_ref"] = forwarded_id
    elif ref:
        context.user_data["last_ref"] = ref

    try:
        if forwarded_id:
            chat = await context.bot.get_chat(forwarded_id)
        else:
            chat = await resolve_channel(context.bot, ref)
    except TelegramError as exc:
        await message.reply_text(
            "❌ Channel nahi mil gaya.\n\n"
            f"Reason: <code>{_esc(exc)}</code>\n\n"
            "<b>Ye 3 cheezein check kariye:</b>\n"
            "1️⃣ Bot channel me <b>Admin</b> hai? (Post messages ✅)\n"
            "2️⃣ <b>@username</b> bheja hai? Channel ka display name (jaise \"My Movies\") "
            "se channel nahi milta\n"
            "3️⃣ Private channel? Us channel ki koi <b>post yahan forward</b> kar dijiye\n\n"
            "Ya <code>-100...</code> wali channel ID bhejiye.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.retry_kb(),
        )
        return None

    if getattr(chat, "type", "") != "channel":
        await message.reply_text(
            "❌ Yeh channel nahi hai.\n\n"
            "Sirf Telegram <b>channel</b> connect ho sakta hai — group ya private chat nahi.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.retry_kb(),
        )
        return None

    ok, reason = await bot_can_post(context.bot, chat.id)
    if not ok:
        uname = await bot_username(context)
        await message.reply_text(
            f"✅ Channel mil gaya: <b>{_esc(chat.title)}</b>\n"
            "❌ Par bot is channel me <b>Admin</b> nahi hai.\n\n"
            f"<b>Kya hua:</b> {_esc(reason)}\n\n"
            "<b>Ab ye 3 step kariye:</b>\n"
            f"1️⃣ Telegram me channel <b>{_esc(chat.title)}</b> kholein\n"
            "2️⃣ Administrators → <b>Add Admin</b> → search kariye "
            f"<code>@{_esc(uname)}</code>\n"
            "3️⃣ <b>Post messages</b> ✅ on karke Save kariye\n\n"
            "Phir neeche <b>Retry</b> dabaiye — username dobara likhne ki zaroorat nahi.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.retry_kb(),
        )
        return None

    return chat


async def connect_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    text = (message.text or "").strip()

    if not text and not channel_ref_from_message(message):
        await message.reply_text(
            "Channel ka <b>@username</b> bhejiye, ya channel ki koi post forward kariye.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.cancel_kb(),
        )
        return CONNECT_CHANNEL

    chat = await _process_channel_input(update, context, text)
    if chat is None:
        return CONNECT_CHANNEL

    return await _ask_owner(update, context, chat)


async def _ask_owner(update: Update, context: ContextTypes.DEFAULT_TYPE, chat) -> int:
    """Channel mil gaya — ab owner ka naam poocho."""
    context.user_data["connect"] = {
        "chat_id": chat.id,
        "username": chat.username,
        "title": chat.title,
    }
    await update.effective_message.reply_text(
        ui.connect_step2(chat.title),
        parse_mode=ParseMode.HTML,
        reply_markup=ui.skipowner_kb(),
    )
    return CONNECT_OWNER


async def retry_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin add karne ke baad ek tap me dobara check — username dobara nahi."""
    query = update.callback_query
    if query:
        await query.answer("Check kar raha hoon…")

    ref = context.user_data.get("last_ref")
    if not ref:
        return await connect_start(update, context)

    context.user_data.setdefault("connect", {})
    chat = await _process_channel_input(update, context, str(ref))
    if chat is None:
        return CONNECT_CHANNEL

    return await _ask_owner(update, context, chat)


async def connect_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.message.text or "").strip()
    if len(name) < 2 or len(name) > 64:
        await update.message.reply_text(
            "Naam 2 se 64 characters ka hona chahiye. Dobara bhejiye — "
            "ya neeche <b>Skip</b> dabaiye.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.skipowner_kb(),
        )
        return CONNECT_OWNER

    context.user_data.setdefault("connect", {})["owner_name"] = name
    await update.message.reply_text(
        ui.connect_step3(name),
        parse_mode=ParseMode.HTML,
        reply_markup=ui.cancel_kb(),
    )
    return CONNECT_PHONE


async def skip_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault("connect", {})
    name = data.get("title") or "Not provided"
    data["owner_name"] = name
    await _reply(update, ui.connect_step3(name), ui.cancel_kb())
    return CONNECT_PHONE


async def connect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.message.text or "").strip()
    digits = re.sub(r"\D", "", raw)

    if not PHONE_RE.match(raw) or len(digits) < 10:
        await update.message.reply_text(
            "❌ Number sahi nahi lag raha.\n\n"
            "Aise bhejiye: <code>+919876543210</code> ya <code>9876543210</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.cancel_kb(),
        )
        return CONNECT_PHONE

    data = context.user_data.get("connect") or {}
    if not data.get("chat_id"):
        await update.message.reply_text("Session expire ho gaya. /connect dobara bhejiye.")
        return ConversationHandler.END

    data["owner_name"] = data.get("owner_name") or data.get("title") or "Not provided"
    return await _finalize_connect(update, context, data, _normalize_phone(raw))


async def _finalize_connect(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict, phone: str
) -> int:
    """Admin verification + DB save + success message."""
    message = update.effective_message
    chat_id = data.get("chat_id")
    if not chat_id:
        await message.reply_text("Session expire ho gaya. /connect dobara bhejiye.")
        return ConversationHandler.END

    # Asli verification — Telegram ke channel admin rights se
    if not await is_channel_admin(context.bot, chat_id, update.effective_user.id):
        context.user_data.pop("connect", None)
        await message.reply_text(
            ui.NOT_ADMIN,
            parse_mode=ParseMode.HTML,
            reply_markup=ui.connect_required_kb(),
        )
        return ConversationHandler.END

    # Channel kisi aur ne pehle se joda hai?
    existing = db(context).channel_by_chat(chat_id)
    if existing and existing["connected_by"] != update.effective_user.id:
        context.user_data.pop("connect", None)
        await message.reply_text(
            "ℹ️ Yeh channel pehle se kisi doosre admin ne connect kiya hua hai.\n\n"
            "Usse <code>/disconnect</code> karwaiye, phir aap connect kariye.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.back_kb(),
        )
        return ConversationHandler.END

    db(context).save_channel(
        chat_id=chat_id,
        username=data.get("username"),
        title=data.get("title") or "Channel",
        owner_name=data["owner_name"],
        admin_phone=phone,
        connected_by=update.effective_user.id,
    )
    row = db(context).channel_by_chat(chat_id)
    context.user_data.pop("connect", None)

    await message.reply_text(
        ui.connected_text(row),
        parse_mode=ParseMode.HTML,
        reply_markup=ui.main_menu(True),
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


# ---------------------------------------------------------------- upload conversation


async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    db(context).touch_user(user.id, user.username, user.full_name)

    row = db(context).channel_of(user.id)
    if not row:
        await _reply(
            update,
            "❌ Pehle channel connect karna hoga.\n\nNeeche <b>Connect Channel</b> dabaiye.",
            ui.connect_required_kb(),
        )
        return ConversationHandler.END

    if not await is_channel_admin(context.bot, row["chat_id"], user.id):
        await _reply(update, ui.NOT_ADMIN, ui.back_kb())
        return ConversationHandler.END

    context.user_data.pop("pending_doc", None)
    await _reply(update, ui.upload_prompt(row), ui.cancel_kb())
    return UPLOAD_FILE


async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    doc = message.document

    if doc is None:
        await message.reply_text(
            "❌ File <b>document</b> ke roop me bhejiye (paperclip 📎 → File).",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.cancel_kb(),
        )
        return UPLOAD_FILE

    name = doc.file_name or f"file_{doc.file_unique_id}"
    ext = os.path.splitext(name)[1].lower()

    if ext not in config.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(e.upper().lstrip(".") for e in config.ALLOWED_EXTENSIONS))
        await message.reply_text(
            f"❌ <code>{_esc(ext or 'unknown')}</code> allowed nahi hai.\n\n"
            f"Allowed: {allowed}",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.cancel_kb(),
        )
        return UPLOAD_FILE

    size = doc.file_size or 0
    if size > config.MAX_FILE_MB * 1024 * 1024:
        await message.reply_text(
            f"❌ File {size / (1024 * 1024):.1f} MB hai — limit {config.MAX_FILE_MB} MB hai.\n\n"
            "Badi file ke liye bot ko local Bot API server par chalana padta hai.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.cancel_kb(),
        )
        return UPLOAD_FILE

    context.user_data["pending_doc"] = {
        "file_id": doc.file_id,
        "name": name,
        "ext": ext,
        "size": size,
    }

    caption = (message.caption or "").strip()
    if caption:
        return await _publish(update, context, caption)

    await message.reply_text(
        f"✅ File mil gayi: <code>{_esc(name)}</code> ({size / (1024 * 1024):.1f} MB)\n\n"
        "Ab <b>description</b> likhiye — jo channel post me dikhega.\n"
        "Skip karna ho to neeche <b>Skip description</b> dabaiye.",
        parse_mode=ParseMode.HTML,
        reply_markup=ui.skip_kb(),
    )
    return UPLOAD_DESC


async def upload_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        description = ""
    else:
        description = (update.message.text or "").strip()
        if len(description) > 800:
            await update.message.reply_text(
                "Description 800 characters se chhoti rakhiye. Dobara bhejiye.",
                reply_markup=ui.skip_kb(),
            )
            return UPLOAD_DESC
    return await _publish(update, context, description)


async def _publish(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> int:
    user = update.effective_user
    info = context.user_data.get("pending_doc")
    row = db(context).channel_of(user.id)

    if not info or not row:
        await _reply(update, "❌ Session expire ho gaya. <code>/apk add</code> dobara bhejiye.", ui.back_kb())
        return ConversationHandler.END

    chat_id = row["chat_id"]
    title = os.path.splitext(info["name"])[0].replace("_", " ").replace("-", " ").strip() or "New File"
    caption = build_caption(title, description, info, user)

    try:
        sent = await context.bot.send_document(
            chat_id=chat_id,
            document=info["file_id"],
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as exc:
        log.warning("Upload failed for chat %s: %s", chat_id, exc)
        await _reply(
            update,
            "❌ Upload fail ho gaya.\n\n"
            f"Reason: <code>{_esc(exc)}</code>\n\n"
            "Check kariye: bot channel me admin hai? 'Post messages' permission on hai?\n"
            "Phir <code>/apk add</code> se dobara try kariye.",
            ui.back_kb(),
        )
        return ConversationHandler.END

    db(context).log_upload(
        chat_id=chat_id,
        user_id=user.id,
        file_name=info["name"],
        file_type=info["ext"].lstrip(".").upper(),
        file_size=info["size"],
        title=title,
        description=description,
        message_id=sent.message_id,
    )
    context.user_data.pop("pending_doc", None)

    if row["username"]:
        link = f"https://t.me/{row['username']}/{sent.message_id}"
        link_line = f"\n🔗 <a href=\"{link}\">Channel post kholiye</a>"
    else:
        link_line = ""

    await _reply(
        update,
        "✅ <b>Upload ho gaya!</b>\n\n"
        f"📢 Channel: <b>{_esc(row['title'])}</b>\n"
        f"📦 File: <code>{_esc(info['name'])}</code>"
        f"{link_line}\n\n"
        "Ek aur file bhejne ke liye <code>/apk add</code>.",
        ui.main_menu(True),
    )
    return ConversationHandler.END


# ---------------------------------------------------------------- status / list / disconnect


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    row = db(context).channel_of(user.id)
    if not row:
        await _reply(update, "❌ Koi channel connected nahi hai.", ui.connect_required_kb())
        return

    ok, reason = await bot_can_post(context.bot, row["chat_id"])
    admin = await is_channel_admin(context.bot, row["chat_id"], user.id)
    total = db(context).upload_count(row["chat_id"])
    ch = f"@{row['username']}" if row["username"] else f"<code>{row['chat_id']}</code>"

    await _reply(
        update,
        "📊 <b>Channel Status</b>\n\n"
        f"📢 {_esc(row['title'])}\n"
        f"🆔 {ch}\n"
        f"👤 Owner: {_esc(row['owner_name'])}\n"
        f"📱 Admin phone: <code>{_esc(row['admin_phone'])}</code>\n"
        f"🕒 Connected: {_esc(row['connected_at'])}\n\n"
        f"🤖 Bot posting: {'✅ ready' if ok else '⚠️ ' + _esc(reason)}\n"
        f"🔐 Aap admin: {'✅ haan' if admin else '❌ nahi'}\n"
        f"📤 Total uploads: <b>{total}</b>",
        ui.main_menu(True),
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    row = db(context).channel_of(update.effective_user.id)
    if not row:
        await _reply(update, "❌ Koi channel connected nahi hai.", ui.connect_required_kb())
        return

    rows = db(context).recent_uploads(row["chat_id"], 10)
    if not rows:
        await _reply(update, "🗂 Abhi tak koi upload nahi hua.", ui.main_menu(True))
        return

    lines = ["🗂 <b>Last uploads</b>\n"]
    for r in rows:
        lines.append(
            f"• <b>{_esc(r['title'])}</b> — {_esc(r['file_type'])} · "
            f"{(r['file_size'] or 0) / (1024 * 1024):.1f} MB\n"
            f"  <i>{_esc(r['created_at'])}</i>"
        )
    await _reply(update, "\n".join(lines), ui.main_menu(True))


async def cmd_disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    row = db(context).channel_of(update.effective_user.id)
    if not row:
        await _reply(update, "ℹ️ Koi channel connected nahi hai.", ui.connect_required_kb())
        return

    await _reply(
        update,
        f"⚠️ <b>{_esc(row['title'])}</b> disconnect karna hai?\n\n"
        "Iske baad is channel me upload nahi ho payega. "
        "Purani upload history DB me rahegi.",
        ui.confirm_disconnect_kb(),
    )


async def disconnect_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    row = db(context).channel_of(update.effective_user.id)
    if row:
        db(context).delete_channel(row["chat_id"])
    await _reply(
        update,
        "✅ Channel disconnect ho gaya.\n\nDobara jodne ke liye <b>Connect Channel</b> dabaiye.",
        ui.connect_required_kb(),
    )


# ---------------------------------------------------------------- cancel / fallbacks


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.pop("pending_doc", None)
    context.user_data.pop("connect", None)
    row = db(context).channel_of(update.effective_user.id)
    await _reply(update, "❎ Cancel kar diya.", ui.main_menu(bool(row)))
    return ConversationHandler.END


async def stray_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row = db(context).channel_of(update.effective_user.id)
    await update.message.reply_text(
        ui.STRAY_DOC,
        parse_mode=ParseMode.HTML,
        reply_markup=ui.main_menu(bool(row)),
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Samajh nahi aaya. /start bhejiye ya /help dekhiye."
    )


async def auto_connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Button dabaye bina — seedha @username / link / forward bhejne par bhi connect."""
    message = update.message
    user = update.effective_user
    db(context).touch_user(user.id, user.username, user.full_name)

    existing = db(context).channel_of(user.id)
    if existing:
        await message.reply_text(
            ui.ALREADY_CONNECTED,
            parse_mode=ParseMode.HTML,
            reply_markup=ui.main_menu(True),
        )
        return ConversationHandler.END

    context.user_data["connect"] = {}
    chat = await _process_channel_input(update, context, (message.text or "").strip())
    if chat is None:
        return CONNECT_CHANNEL

    return await _ask_owner(update, context, chat)


async def stray_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Samajh na aane wala message — bot chup na rahe, raasta dikhaye."""
    message = update.message
    user = update.effective_user
    text = (message.text or "").strip()
    log.info("stray text from %s (@%s): %r", user.id, user.username, text[:80])
    db(context).touch_user(user.id, user.username, user.full_name)

    row = db(context).channel_of(user.id)
    if row:
        await message.reply_text(
            "📤 File bhejne ke liye <code>/apk add</code> bhejiye.\n"
            "Channel badalna ho to <code>/disconnect</code>.",
            parse_mode=ParseMode.HTML,
            reply_markup=ui.main_menu(True),
        )
        return

    await message.reply_text(
        "🔗 Pehle channel connect kariye.\n\n"
        "Neeche <b>Connect Channel</b> dabaiye — ya seedha channel ka "
        "<code>@username</code> bhej dijiye.",
        parse_mode=ParseMode.HTML,
        reply_markup=ui.connect_required_kb(),
    )


# ---------------------------------------------------------------- registration


def register(app) -> None:
    """Saare handlers application me jodta hai."""

    connect_conv = ConversationHandler(
        entry_points=[
            CommandHandler("connect", connect_start),
            CallbackQueryHandler(connect_start, pattern=r"^connect$"),
            # Button dabaye bina bhi kaam kare:
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(CHANNEL_REF_RE),
                auto_connect,
            ),
            MessageHandler(IsChannelForward(), auto_connect),
        ],
        states={
            CONNECT_CHANNEL: [
                CallbackQueryHandler(retry_check, pattern=r"^retry$"),
                MessageHandler(IsChannelForward(), connect_channel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, connect_channel),
            ],
            CONNECT_OWNER: [
                CallbackQueryHandler(skip_owner, pattern=r"^skipowner$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, connect_owner),
            ],
            CONNECT_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, connect_phone)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cmd_cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    upload_conv = ConversationHandler(
        entry_points=[
            CommandHandler(["apk", "add", "upload"], upload_start),
            CallbackQueryHandler(upload_start, pattern=r"^upload$"),
        ],
        states={
            UPLOAD_FILE: [
                MessageHandler(filters.Document.ALL, upload_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _need_document),
            ],
            UPLOAD_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upload_desc),
                CallbackQueryHandler(upload_desc, pattern=r"^skipdesc$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cmd_cancel, pattern=r"^cancel$"),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("disconnect", cmd_disconnect))
    app.add_handler(CommandHandler(["diag", "debug"], cmd_diag))

    app.add_handler(connect_conv)
    app.add_handler(upload_conv)

    app.add_handler(CallbackQueryHandler(retry_check, pattern=r"^retry$"))
    app.add_handler(CallbackQueryHandler(cmd_menu, pattern=r"^menu$"))
    app.add_handler(CallbackQueryHandler(cmd_about, pattern=r"^about$"))
    app.add_handler(CallbackQueryHandler(cmd_status, pattern=r"^status$"))
    app.add_handler(CallbackQueryHandler(cmd_list, pattern=r"^list$"))
    app.add_handler(CallbackQueryHandler(cmd_disconnect, pattern=r"^disconnect$"))
    app.add_handler(CallbackQueryHandler(disconnect_confirm, pattern=r"^disc_yes$"))

    app.add_handler(MessageHandler(filters.Document.ALL, stray_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stray_text))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))


async def _need_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ File <b>document</b> ke roop me bhejiye (📎 → File).\n"
        "Text nahi, file chahiye.",
        parse_mode=ParseMode.HTML,
        reply_markup=ui.cancel_kb(),
    )
    return UPLOAD_FILE
