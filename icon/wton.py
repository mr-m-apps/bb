import asyncio
from pathlib import Path
import argparse
import sys
import logging
from typing import List, Tuple
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.error import TelegramError, RetryAfter, Forbidden, BadRequest

BOT_TOKEN = "7609516607:AAH3HCBQMN4JTTwxl12gBktjJfCUiwK3pfU"

ID_SOURCE = "https://raw.githubusercontent.com/elsoghiar/image/refs/heads/main/sparks_ids.txt"

MESSAGE_TEXT = (
    "🔥 <b>The Airdrop Has Started — Claim What’s Yours!</b>\n\n"
    "💰 Your full reward pool is now unlocked — and each token is worth over <b>$0.5</b>!\n"
    "⛽ Just cover the gas fee and the entire collection is instantly yours.\n\n"
    "🎉 You’re not getting tokens — you’re getting thousands in future value.\n"
    "💸 Claim now and own the moment before it’s gone.\n\n"
    "👇 Tap below to unlock your full stack."
)

BUTTONS: List[Tuple[str, str]] = [
    ("Claim Now 🎉", "https://t.me/xSparks_Bot/app"),
    ("Join The Community", "https://t.me/xSparksio")
]
IMAGE_URL = ""
MAX_MSGS_PER_SECOND = 25

logging.basicConfig(format="%(levelname)s | %(message)s", level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("broadcast")

def load_ids(src: str) -> List[int]:
    if src.startswith(("http://", "https://")):
        txt = requests.get(src, timeout=10).text
        lines = txt.splitlines()
    else:
        lines = Path(src).read_text(encoding="utf-8").splitlines()
    return [int(line.strip()) for line in lines if line.strip().isdigit()]

def build_keyboard(buttons: List[Tuple[str, str]]):
    if not buttons:
        return None
    return InlineKeyboardMarkup.from_column([InlineKeyboardButton(text, url=url) for text, url in buttons])

async def send_to_user(bot: Bot, chat_id: int, text: str, kb, image_url: str):
    try:
        if image_url:
            await bot.send_photo(chat_id=chat_id, photo=image_url, caption=text, parse_mode=constants.ParseMode.HTML, reply_markup=kb)
        else:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=constants.ParseMode.HTML, reply_markup=kb)
    except Forbidden:
        pass
    except BadRequest:
        pass
    except RetryAfter as e:
        await asyncio.sleep(int(e.retry_after) + 1)
        await send_to_user(bot, chat_id, text, kb, image_url)
    except TelegramError:
        pass

async def broadcaster(bot: Bot, ids: List[int], text: str, kb, image_url: str):
    sem = asyncio.Semaphore(MAX_MSGS_PER_SECOND)
    async def worker(chat_id: int):
        async with sem:
            await send_to_user(bot, chat_id, text, kb, image_url)
            await asyncio.sleep(1 / MAX_MSGS_PER_SECOND)
    await asyncio.gather(*(worker(uid) for uid in ids))

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--token", default=BOT_TOKEN)
    p.add_argument("--source", default=ID_SOURCE)
    p.add_argument("--text", default=MESSAGE_TEXT)
    p.add_argument("--image", default=IMAGE_URL)
    p.add_argument("--button", action="append", nargs=2, metavar=("LABEL", "URL"))
    p.add_argument("--speed", type=int, default=MAX_MSGS_PER_SECOND)
    return p.parse_args()

async def main():
    args = parse_args()
    global MAX_MSGS_PER_SECOND
    MAX_MSGS_PER_SECOND = min(args.speed, 30)
    ids = load_ids(args.source)
    if not ids:
        log.error("No valid IDs found")
        return
    buttons = args.button if args.button else BUTTONS
    kb = build_keyboard(buttons)
    bot = Bot(args.token)
    await broadcaster(bot, ids, args.text, kb, args.image)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
