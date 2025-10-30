import io, csv
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from bot.services.admins import is_admin, grant_admin, revoke_admin
from bot.services.partners import add_partner, create_link
from bot.services.stats import totals, last_clicks
from bot.db import db
from bot.config import settings

router = Router(name="admin")

@router.message(Command("admin"))
async def admin_panel(m: Message):
    if not await is_admin(m.from_user.id):
        return await m.answer("⛔️ Admins only.")
    await m.answer(
        "<b>Admin</b>\n"
        "• /admins — список адмінів\n"
        "• /admin_grant <uid>\n"
        "• /admin_revoke <uid>\n"
        "• /partners_add <code> <name> <base_url>\n"
        "• /link_new <code> [note]\n"
        "• /stats — загальна статистика\n"
        "• /clicks [N] — останні переходи\n"
        "• /leads [status] — заявки\n"
        "• /lead <id> — перегляд\n"
        "• /lead_status <id> <new_status>\n"
        "• /leads_csv — експорт\n"
    )

@router.message(Command("admins"))
async def admins_list(m: Message):
    if not await is_admin(m.from_user.id): return
    rows = await db.fetchall("SELECT user_id, added_at FROM admins ORDER BY added_at DESC")
    env_info = f"(також із .env ADMIN_IDS: {', '.join(settings.ADMIN_IDS)})"
    if not rows:
        return await m.answer("Адмінів у БД нема. " + env_info)
    msg = "<b>Адміни (БД)</b>\n" + "\n".join(f"• {r['user_id']} (з {r['added_at']})" for r in rows)
    await m.answer(msg + f"\n\n{env_info}")

@router.message(Command("admin_grant"))
async def admin_grant_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Формат: /admin_grant <uid>")
    await grant_admin(int(parts[1]))
    await m.answer("✅ Готово")

@router.message(Command("admin_revoke"))
async def admin_revoke_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Формат: /admin_revoke <uid>")
    await revoke_admin(int(parts[1]))
    await m.answer("✅ Готово")

@router.message(Command("partners_add"))
async def partners_add_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    try:
        _, code, name, base_url = m.text.split(maxsplit=3)
    except Exception:
        return await m.answer("Формат: /partners_add <code> <name> <base_url>")
    await add_partner(code, name, base_url)
    await m.answer(f"✅ Додано партнера {name} ({code})")

@router.message(Command("link_new"))
async def link_new_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split(maxsplit=2)
    if len(parts) < 2:
        return await m.answer("Формат: /link_new <code> [note]")
    code = parts[1]
    note = parts[2] if len(parts) == 3 else None
    try:
        slug, base = await create_link(code, note, m.from_user.id)
    except ValueError as e:
        return await m.answer(f"Помилка: {e}")
    short = f"{settings.PUBLIC_REDIRECT_BASE}/{slug}"
    me = f"{short}?tg={m.from_user.id}"
    await m.answer(f"🔗 Створено:\n{short}\n👤 Персональний: {me}\n📍 Веде на: {base}\nNote: {note or '-'}")

@router.message(Command("stats"))
async def stats_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    users, views, payouts_sum = await totals()
    await m.answer(
        "<b>Статистика</b>\n"
        f"Користувачів: <b>{users}</b>\n"
        f"Переглядів: <b>{views}</b>\n"
        f"Нараховано: <b>{payouts_sum:.2f} USDT</b>"
    )

@router.message(Command("clicks"))
async def clicks_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    n = 10
    parts = m.text.split()
    if len(parts) == 2 and parts[1].isdigit():
        n = min(100, int(parts[1]))
    rows = await last_clicks(n)
    if not rows: return await m.answer("Немає переходів.")
    msg = "<b>Останні переходи</b>\n" + "\n".join(
        f"#{r['id']} [{r['ts']}] slug={r['link_slug']} uid={r['user_id'] or '-'} ip={r['ip']} ref={r['ref'] or '-'}"
        for r in rows
    )
    await m.answer(msg)

@router.message(Command("leads"))
async def leads_list_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split()
    status = parts[1] if len(parts) > 1 else None
    base_q = "SELECT id, created_at, user_id, destination, date_from, date_to, status FROM leads"
    rows = await db.fetchall(
        (base_q + " WHERE status=? ORDER BY id DESC LIMIT 20") if status else (base_q + " ORDER BY id DESC LIMIT 20"),
        (status,) if status else ()
    )
    if not rows: return await m.answer("Заявок нема.")
    txt = "<b>Останні заявки</b>\n" + "\n".join(
        f"#{r['id']} [{r['created_at']}] {r['destination']} {r['date_from']}–{r['date_to']} uid={r['user_id']} status={r['status']}"
        for r in rows
    )
    await m.answer(txt)

@router.message(Command("lead"))
async def lead_view_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Формат: /lead <id>")
    r = await db.fetchone("SELECT * FROM leads WHERE id=?", (int(parts[1]),))
    if not r: return await m.answer("Не знайдено.")
    await m.answer(
        f"<b>Заявка #{r['id']}</b>\n"
        f"Користувач: {r['user_id']}\n"
        f"Напрямок: {r['destination']}\nДати: {r['date_from']}—{r['date_to']}\n"
        f"Пакс: {r['pax']}\nБюджет: {r['budget']}\nПобажання: {r['notes']}\n"
        f"Статус: {r['status']}\nПартнер: {r['partner_code'] or '-'}\nЛінк: {r['link_slug'] or '-'}"
    )

@router.message(Command("lead_status"))
async def lead_status_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    parts = m.text.split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit():
        return await m.answer("Формат: /lead_status <id> <new_status>")
    await db.execute("UPDATE leads SET status=? WHERE id=?", (parts[2], int(parts[1])))
    await m.answer("✅ Оновлено.")

@router.message(Command("leads_csv"))
async def leads_csv_cmd(m: Message):
    if not await is_admin(m.from_user.id): return
    rows = await db.fetchall("""
        SELECT id, created_at, user_id, status, destination, date_from, date_to, pax, budget, notes, partner_code, link_slug
        FROM leads ORDER BY id DESC LIMIT 1000
    """)
    if not rows:
        return await m.answer("Заявок нема.")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","created_at","user_id","status","destination","date_from","date_to","pax","budget","notes","partner_code","link_slug"])
    for r in rows:
        w.writerow([r["id"], r["created_at"], r["user_id"], r["status"], r["destination"], r["date_from"], r["date_to"],
                    r["pax"], r["budget"], r["notes"], r["partner_code"], r["link_slug"]])
    mem = io.BytesIO(buf.getvalue().encode("utf-8"))
    await m.answer_document(FSInputFile(mem, filename="leads.csv"), caption="📄 leads.csv")
