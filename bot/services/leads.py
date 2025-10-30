from bot.db import db

async def create_draft(user_id: int, destination: str) -> int:
    await db.execute("INSERT INTO leads (user_id, destination) VALUES (?,?)", (user_id, destination))
    row = await db.fetchone("SELECT last_insert_rowid() AS id")
    return row["id"] if row else 0

async def update_draft(user_id: int, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    vals = list(fields.values()) + [user_id]
    await db.execute(f"UPDATE leads SET {sets} WHERE user_id=? AND status='new' ORDER BY id DESC LIMIT 1", vals)
