from bot.db import db

SUPPORTED_LANGS = ("uk", "en")

def detect_lang_code(tg_code: str) -> str:
    return "en" if (tg_code or "").lower().startswith("en") else "uk"

async def get_lang(user_id: int, tg_code: str | None = None) -> str:
    row = await db.fetchone("SELECT lang FROM user_prefs WHERE user_id=?", (user_id,))
    if row and row["lang"] in SUPPORTED_LANGS:
        return row["lang"]
    lang = detect_lang_code(tg_code)
    await db.execute("INSERT OR REPLACE INTO user_prefs (user_id, lang) VALUES (?,?)", (user_id, lang))
    return lang

async def set_lang(user_id: int, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = "uk"
    await db.execute("INSERT OR REPLACE INTO user_prefs (user_id, lang) VALUES (?,?)", (user_id, lang))
