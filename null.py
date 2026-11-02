#!/usr/bin/env python3
"""
N4X — Telegram Channel Upload Bot
=================================

Chalane ka tarika:
    export BOT_TOKEN="BotFather ka token"
    python3 null.py

Ya token seedha config.py me BOT_TOKEN ki jagah daal dijiye.

Bot: N4X
Owner: Hari Jadhav · Instagram @ur_.krishn._02 · Telegram @nullkrishn

NOTE (Python 3.14 / Termux):
    Python 3.14 me asyncio.get_event_loop() implicit loop nahi banata, isliye
    python-telegram-bot 22.8+ chahiye. Purani version par:
        pip install -U "python-telegram-bot>=22.8"
    Neeche event loop khud set kar diya jata hai, phir bhi.
"""

import asyncio
import logging
import sys
import warnings

from telegram import BotCommand, Update
from telegram.ext import Application

import config
from database import Database
from handlers import register

# PTB ka "per_message=False" wala warning harmless hai — terminal saaf rakhne ke liye off
try:
    from telegram.warnings import PTBUserWarning

    warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*per_message.*")
except Exception:  # noqa: BLE001
    pass

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("n4x")


def ensure_event_loop() -> None:
    """Python 3.14+ me get_event_loop() crash karta hai — pehle loop set kar dete hain."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        log.info("Naya event loop set kiya (Python %s)", sys.version.split()[0])


def check_versions() -> None:
    import telegram

    major = int(telegram.__version__.split(".")[0])
    if sys.version_info >= (3, 14) and major < 22:
        log.warning(
            "Python %s ke saath python-telegram-bot %s theek nahi chalega. "
            'Chalaiye: pip install -U "python-telegram-bot>=22.8"',
            sys.version.split()[0],
            telegram.__version__,
        )


async def post_init(app: Application) -> None:
    """Bot ke menu me commands set karta hai."""
    await app.bot.set_my_commands([
        BotCommand("start", "Main menu"),
        BotCommand("apk", "APK / ZIP / PDF / TXT upload kariye"),
        BotCommand("connect", "Channel connect kariye"),
        BotCommand("status", "Channel status"),
        BotCommand("list", "Last 10 uploads"),
        BotCommand("disconnect", "Channel remove kariye"),
        BotCommand("about", "Bot aur owner ki details"),
        BotCommand("cancel", "Current step cancel"),
        BotCommand("help", "Help"),
    ])
    me = await app.bot.get_me()
    log.info("Bot online: @%s (%s) — ready", me.username, me.first_name)


async def on_error(update: object, context) -> None:
    log.error("Update me error aaya: %s", context.error, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kuch galat ho gaya. Dobara try kariye ya /start bhejiye."
            )
        except Exception:  # noqa: BLE001
            pass


def main() -> None:
    if not config.BOT_TOKEN or "PUT_YOUR" in config.BOT_TOKEN:
        print(
            "\n❌ BOT_TOKEN set nahi hai.\n\n"
            "Do me se ek kariye:\n"
            '  1) export BOT_TOKEN="123456:ABC..."  phir python3 null.py\n'
            "  2) config.py kholein aur BOT_TOKEN ki jagah apna token daalein\n"
        )
        sys.exit(1)

    check_versions()
    ensure_event_loop()
    log.info("N4X start ho raha hai…")

    database = Database(config.DB_PATH)

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.bot_data["db"] = database

    register(app)
    app.add_error_handler(on_error)

    log.info("Polling shuru — Ctrl+C se band karein")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
