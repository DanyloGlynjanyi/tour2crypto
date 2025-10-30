import ipaddress
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse
from bot.db import db

app = FastAPI(title="T2C Redirect")

@app.on_event("startup")
async def on_start():
    await db.connect()

@app.on_event("shutdown")
async def on_stop():
    await db.close()

def _client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = req.client.host if req.client else "0.0.0.0"
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        ip = "0.0.0.0"
    return ip

@app.get("/r/{slug}")
async def redirect(slug: str, tg: int | None = None, request: Request = None):
    row = await db.fetchone("""
        SELECT l.slug, p.base_url
        FROM links l JOIN partners p ON p.id=l.partner_id
        WHERE l.slug=? AND p.is_active=1
        ORDER BY l.id DESC LIMIT 1
    """, (slug,))
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    dest = row["base_url"]
    ip = _client_ip(request)
    ref = request.headers.get("referer")
    ua = request.headers.get("user-agent")

    await db.execute("""
        INSERT INTO clicks (link_slug, user_id, ip, ref, ua, dest_url)
        VALUES (?,?,?,?,?,?)
    """, (slug, tg, ip, ref, ua, dest))

    return RedirectResponse(url=dest, status_code=302)

@app.get("/")
async def health():
    return PlainTextResponse("OK")
