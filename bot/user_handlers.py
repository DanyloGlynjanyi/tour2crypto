import re
from datetime import datetime
from typing import Optional, Tuple
from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from bot.core import t, main_kb, lang_kb
from bot.db import db
from bot.services.prefs import get_lang, set_lang
from bot.search_providers import aggregate_search
from bot.config import settings

router = Router(name="user")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

async def _ensure_user(message: Message) -> str:
    u = message.from_user
    await db.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?,?,?,?)",
        (u.id, u.username, u.first_name, u.last_name)
    )
    return await get_lang(u.id, u.language_code)

def _valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d"); return True
    except: return False

def _parse_dates(text: str) -> Optional[Tuple[str, str]]:
    normalized = text.replace("—", "-").replace(".", "-")
    dates = DATE_RE.findall(normalized)
    if len(dates) >= 2 and _valid_date(dates[0]) and _valid_date(dates[1]):
        return dates[0], dates[1]
    return None

# /start
@router.message(CommandStart())
async def on_start(m: Message):
    lang = await _ensure_user(m)
    await m.answer(t("welcome", lang), reply_markup=main_kb(lang))
    if str(m.from_user.id) in settings.ADMIN_IDS:
        await m.answer("• /admin — admin panel")

@router.message(Command("help"))
async def cmd_help(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    await m.answer(t("help", lang))

# language
@router.message(F.text.in_(["Мова / Language", "Language / Мова"]) | Command("lang"))
async def choose_lang(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    await m.answer(t("lang_choose", lang), reply_markup=lang_kb())

@router.callback_query(F.data.startswith("lang:"))
async def set_language(cb: types.CallbackQuery):
    _, val = cb.data.split(":", 1)
    await set_lang(cb.from_user.id, val)
    await cb.message.edit_text({"uk":"✅ Мову збережено: Українська","en":"✅ Language saved: English"}[val])
    await cb.answer()

# quick info
@router.message(F.text.in_(["Як це працює", "How it works"]))
async def how_it_works(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    await m.answer(t("help", lang))

@router.message(F.text.in_(["Підтримка", "Support"]))
async def support(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    await m.answer(t("support", lang))

# partners menu (статичний текст з кодами)
@router.message(F.text.in_(["Забронювати зараз", "Book now"]))
async def partners_menu(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    text = (
        "<b>Партнери</b>\n"
        "🏨 Trip.com — код: <code>trip</code>\n"
        "🌴 Agoda — код: <code>agoda</code>\n"
        "🗺️ GetYourGuide — код: <code>gyg</code>\n"
        "✈️ Viator — код: <code>viator</code>\n"
        "🇺🇦 JoinUP — код: <code>join</code>\n\n"
        f"{'Надішли код' if lang=='uk' else 'Send a code'}"
    )
    await m.answer(text)

# partner codes → коротке посилання
@router.message(F.text.func(lambda s: isinstance(s, str) and s.strip().lower() in {"trip","agoda","gyg","viator","join"}))
async def partner_link(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    code = m.text.strip().lower()
    row = await db.fetchone("""
        SELECT l.slug, p.base_url
        FROM links l JOIN partners p ON p.id=l.partner_id
        WHERE p.code=? AND p.is_active=1
        ORDER BY l.id DESC LIMIT 1
    """, (code,))
    if not row:
        return await m.answer("Посилання готуємо, спробуй пізніше." if lang=="uk" else "Link is not ready yet, try later.")
    short = f"{settings.PUBLIC_REDIRECT_BASE}/{row['slug']}?tg={m.from_user.id}"
    name = {"trip":"Trip.com","agoda":"Agoda","gyg":"GetYourGuide","viator":"Viator","join":"JoinUP"}[code]
    await m.answer(f"🔗 <b>{name}</b>\n{('Відкрити пропозиції' if lang=='uk' else 'Open offers')}: {short}")

# /find <city> <from—to> <pax> (поки заглушка)
@router.message(Command("find"))
async def cmd_find(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    parts = (m.text or "").split(maxsplit=1)
    payload = parts[1] if len(parts) > 1 else ""
    if not payload:
        return await m.answer("Формат: /find <місто> <2025-11-10—2025-11-15> <2>" if lang=="uk"
                              else "Format: /find <city> <2025-11-10—2025-11-15> <2>")
    try:
        # на мінімум: беремо останнє слово як pax
        tokens = payload.rsplit(maxsplit=1)
        pax = int(tokens[-1])
        rest = tokens[0]
        # з решти виділяємо дві дати
        dates = _parse_dates(rest)
        if not dates:
            raise ValueError
        date_from, date_to = dates
        city = rest.split()[0]
    except Exception:
        return await m.answer("Не зміг розпізнати. Приклад: /find Барселона 2025-11-10—2025-11-15 2"
                              if lang=="uk" else
                              "Could not parse. Example: /find Barcelona 2025-11-10—2025-11-15 2")
    await m.answer(("🔎 Шукаю для: <b>{}</b> {}—{}, pax={}".format(city, date_from, date_to, pax))
                   if lang=="uk" else
                   ("🔎 Searching for: <b>{}</b> {}—{}, pax={}".format(city, date_from, date_to, pax)))
    results = await aggregate_search(city, date_from, date_to, pax)
    if not results:
        return await m.answer("Поки без результатів (провайдери API незабаром)." if lang=="uk"
                              else "No results yet (providers’ APIs soon).")
    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Пропозиція" if lang=="uk" else "Offer")
        details = r.get("details","")
        prov = r.get("provider","")
        deeplink = r.get("deeplink","")
        price = r.get("price")
        cur = r.get("currency","EUR")
        price_txt = (f"{price:.0f} {cur}" if isinstance(price,(int,float)) and price>0
                     else ("ціна на сайті" if lang=="uk" else "price on site"))
        lines.append(f"{i}. <b>{title}</b>\n   {details}\n   <i>{prov}</i> · {price_txt}\n   {deeplink}")
    await m.answer(("🧭 <b>Результати пошуку</b>\n" if lang=="uk" else "🧭 <b>Search results</b>\n") + "\n\n".join(lines[:8]))

# simple lead flow (чорновик у БД по кроках)
_user_flow = {}  # uid -> step

@router.message(F.text.in_(["Залишити заявку", "Leave a request"]))
async def lead_start(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    _user_flow[m.from_user.id] = "dest"
    await m.answer(t("lead_dest", lang))

@router.message(F.text & (F.from_user.id.func(lambda uid: uid in _user_flow)))
async def lead_steps(m: Message):
    lang = await get_lang(m.from_user.id, m.from_user.language_code)
    step = _user_flow.get(m.from_user.id, "dest")
    text = (m.text or "").strip()

    if step == "dest":
        await db.execute("INSERT INTO leads (user_id, destination) VALUES (?,?)", (m.from_user.id, text))
        _user_flow[m.from_user.id] = "dates"
        return await m.answer(t("lead_dates", lang))

    if step == "dates":
        parsed = _parse_dates(text)
        if not parsed:
            return await m.answer(t("lead_dates", lang))
        date_from, date_to = parsed
        await db.execute(
            "UPDATE leads SET date_from=?, date_to=? WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1",
            (date_from, date_to, m.from_user.id)
        )
        _user_flow[m.from_user.id] = "pax"
        return await m.answer(t("lead_pax", lang))

    if step == "pax":
        try:
            pax = int(text)
            if not (1 <= pax <= 20):
                raise ValueError
        except ValueError:
            return await m.answer(t("lead_pax", lang))
        await db.execute(
            "UPDATE leads SET pax=? WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1",
            (pax, m.from_user.id)
        )
        _user_flow[m.from_user.id] = "budget"
        return await m.answer(t("lead_budget", lang))

    if step == "budget":
        await db.execute(
            "UPDATE leads SET budget=? WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1",
            (text, m.from_user.id)
        )
        _user_flow[m.from_user.id] = "notes"
        return await m.answer(t("lead_notes", lang))

    if step == "notes":
        await db.execute(
            "UPDATE leads SET notes=? WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1",
            (text, m.from_user.id)
        )
        row = await db.fetchone(
            "SELECT id FROM leads WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1",
            (m.from_user.id,)
        )
        _user_flow.pop(m.from_user.id, None)
        lead_id = row["id"] if row else 0
        return await m.answer(t("lead_ok", lang, id=lead_id))
