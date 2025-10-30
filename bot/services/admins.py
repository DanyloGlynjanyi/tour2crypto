from bot.config import settings
from bot.db import db

async def is_admin(user_id: int) -> bool:
    if str(user_id) in settings.ADMIN_IDS:
        return True
    row = await db.fetchone("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    return bool(row)

async def grant_admin(user_id: int):
    await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))

async def revoke_admin(user_id: int):
    await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
