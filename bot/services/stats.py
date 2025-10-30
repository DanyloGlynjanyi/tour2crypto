from bot.db import db

async def totals():
    users = await db.fetchone("SELECT COUNT(*) AS c FROM users")
    clicks = await db.fetchone("SELECT COUNT(*) AS c FROM clicks")
    payouts = await db.fetchone("SELECT IFNULL(SUM(amount_usdt),0) AS s FROM payouts")
    return (users["c"] if users else 0, clicks["c"] if clicks else 0, payouts["s"] if payouts else 0.0)

async def last_clicks(n=10):
    return await db.fetchall(
        "SELECT id, ts, link_slug, user_id, ip, substr(coalesce(ref,''),1,120) AS ref FROM clicks ORDER BY id DESC LIMIT ?",
        (n,)
    )
