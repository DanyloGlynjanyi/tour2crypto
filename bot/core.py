from datetime import datetime
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings

bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

T = {
    "welcome": {
        "uk": "👋 <b>TOUR2CRYPTO</b>\nБронюй у партнерів — отримуй кешбек у USDT. Обери дію нижче:",
        "en": "👋 <b>TOUR2CRYPTO</b>\nBook with partners — earn cashback in USDT. Choose an action below:"
    },
    "help": {
        "uk": "❓ <b>Як це працює</b>\n1) Обери партнера та відкрий пропозиції.\n2) Бронюй на офіційному сайті партнера.\n3) Після підтвердження — кешбек у USDT.\n⏱ 7–30 днів.",
        "en": "❓ <b>How it works</b>\n1) Pick a partner and open offers.\n2) Book on partner’s site.\n3) After confirmation — cashback in USDT.\n⏱ 7–30 days."
    },
    "kb_book_now": {"uk":"Забронювати зараз","en":"Book now"},
    "kb_leave_request": {"uk":"Залишити заявку","en":"Leave a request"},
    "kb_how": {"uk":"Як це працює","en":"How it works"},
    "kb_support": {"uk":"Підтримка","en":"Support"},
    "kb_language": {"uk":"Мова / Language","en":"Language / Мова"},
    "lead_dest": {"uk":"Куди плануєш їхати? (місто/країна)","en":"Where do you plan to go? (city/country)"},
    "lead_dates":{"uk":"Дати поїздки? (YYYY-MM-DD—YYYY-MM-DD)","en":"Trip dates? (YYYY-MM-DD—YYYY-MM-DD)"},
    "lead_pax":{"uk":"Скільки людей?","en":"How many people?"},
    "lead_budget":{"uk":"Орієнтовний бюджет? (наприклад: до 500€)","en":"Approximate budget? (e.g., up to €500)"},
    "lead_notes":{"uk":"Побажання? Або напиши “без побажань”.","en":"Any preferences? Or type “no preferences”.",
    },
    "lead_ok":{"uk":"✅ Прийнято! Заявка #{id}. Підберемо варіанти й надішлемо лінк.",
               "en":"✅ Received! Request #{id}. We’ll prepare options and send a link."},
    "lang_choose":{"uk":"Оберіть мову / Choose language:","en":"Choose language / Оберіть мову:"},
    "support":{"uk":"Пишіть питання одним повідомленням — відповімо скоро.","en":"Send your question in one message — we’ll reply soon."},
    "stats": {
        "uk": "<b>Статистика</b>\nКористувачів: <b>{users}</b>\nПереглядів: <b>{views}</b>\nНараховано: <b>{payouts:.2f} USDT</b>",
        "en": "<b>Stats</b>\nUsers: <b>{users}</b>\nViews: <b>{views}</b>\nAccrued: <b>{payouts:.2f} USDT</b>"
    },
}

def t(key: str, lang: str, **fmt) -> str:
    s = T.get(key, {}).get(lang) or T.get(key, {}).get("uk") or ""
    return s.format(**fmt) if fmt else s

def main_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=T["kb_book_now"][lang]), KeyboardButton(text=T["kb_leave_request"][lang])],
            [KeyboardButton(text=T["kb_how"][lang]), KeyboardButton(text=T["kb_support"][lang])],
            [KeyboardButton(text=T["kb_language"][lang])]
        ],
        resize_keyboard=True
    )

def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Українська", callback_data="lang:uk"),
        InlineKeyboardButton(text="English",   callback_data="lang:en"),
    ]])

__all__ = ["bot","t","main_kb","lang_kb","now_str","settings"]
