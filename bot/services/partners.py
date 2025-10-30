import secrets, string
from bot.db import db

def _slug(n=8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

async def add_partner(code: str, name: str, base_url: str):
    await db.execute("INSERT INTO partners (code,name,base_url) VALUES (?,?,?)", (code, name, base_url))

async def create_link(code: str, note: str | None, created_by: int) -> tuple[str, str]:
    p = await db.fetchone("SELECT id, base_url FROM partners WHERE code=? AND is_active=1", (code,))
    if not p:
        raise ValueError("Partner not found or inactive")
    slug = _slug()
    await db.execute(
        "INSERT INTO links (slug,partner_id,note,created_by) VALUES (?,?,?,?)",
        (slug, p["id"], note, created_by)
    )
    return slug, p["base_url"]
