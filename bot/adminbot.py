#!/usr/bin/env python3
"""SAMA BASIC — admin bot + buyurtma API.

Nima qiladi:
  1. HTTP API (POST /api/order) — site/landing buyurtmani qabul qiladi,
     SQLite bazaga yozadi va adminlarga inline tugmali xabar yuboradi.
  2. Telegram long-polling — /start, /orders, /stats buyruqlari va
     inline tugmalar (Qabul / Rad / Tayyorlanmoqda / Yo'lda / Yetkazildi).

Faqat Python standart kutubxonasi (o'rnatish shart emas).
Ishga tushirish:  python adminbot.py
"""
import json
import re
import sqlite3
import threading
import time
import mimetypes
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import os

# ---------- Sozlama ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8975220527:AAHXUl4SixHdXAELqOdVWtU8WwZz3M3jASY")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "7692914031,7148674443").split(",") if x.strip()]
HTTP_PORT = int(os.environ.get("PORT", "8003"))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.db")

STATUS = {
    "new": "🆕 Yangi",
    "awaiting_payment": "⏳ To'lov kutilmoqda",
    "awaiting_confirm": "🔎 Chek tekshirilmoqda",
    "accepted": "✅ Qabul qilindi",
    "preparing": "🟡 Tayyorlanmoqda",
    "delivering": "🚚 Yo'lda",
    "delivered": "🏁 Yetkazildi",
    "closed": "🎉 Yakunlandi",
    "cancelled": "❌ Bekor qilindi",
    "rejected": "⛔ Rad etildi",
}

BOT_USERNAME = os.environ.get("BOT_USERNAME", "samabasicbot")

# ---------- Telegram API ----------
def tg(method, payload=None, timeout=25):
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "description": f"tarmoq: {e}"}


def fmt(n):
    try:
        return f"{int(n):,}".replace(",", " ") + " so'm"
    except (ValueError, TypeError):
        return str(n)


def esc(s):
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- Baza ----------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        no TEXT, source TEXT, name TEXT, phone TEXT, email TEXT,
        address TEXT, ship TEXT, pay TEXT, note TEXT,
        items TEXT, subtotal INTEGER, ship_cost INTEGER, total INTEGER,
        lat REAL, lon REAL, status TEXT DEFAULT 'new',
        msgs TEXT DEFAULT '[]', created_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS promos(
        code TEXT PRIMARY KEY, pct INTEGER, max_uses INTEGER DEFAULT 0,
        used INTEGER DEFAULT 0, active INTEGER DEFAULT 1, created_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, cat TEXT DEFAULT 'kiyimlar', price INTEGER DEFAULT 0, old INTEGER DEFAULT 0,
        material TEXT DEFAULT '', sizes TEXT DEFAULT '', colors TEXT DEFAULT '',
        stock INTEGER DEFAULT 10, descr TEXT DEFAULT '', care TEXT DEFAULT '', tag TEXT DEFAULT '',
        img TEXT DEFAULT '', active INTEGER DEFAULT 1, created_at TEXT)""")
    for col in ("promo TEXT DEFAULT ''", "discount INTEGER DEFAULT 0",
                "discount_pct INTEGER DEFAULT 0", "prepay INTEGER DEFAULT 0",
                "tg_user INTEGER DEFAULT 0", "check_file TEXT DEFAULT ''"):
        try:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    con.commit()
    con.close()


def save_order(d):
    con = db()
    cur = con.execute(
        """INSERT INTO orders(no,source,name,phone,email,address,ship,pay,note,
           items,subtotal,ship_cost,total,lat,lon,status,created_at,
           promo,discount,discount_pct,prepay)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'awaiting_payment',?,?,?,?,?)""",
        (d.get("no"), d.get("source"), d.get("name"), d.get("phone"), d.get("email"),
         d.get("address"), d.get("ship"), d.get("pay"), d.get("note"),
         json.dumps(d.get("items", []), ensure_ascii=False),
         int(d.get("subtotal", 0)), int(d.get("shipCost", 0)), int(d.get("total", 0)),
         (d.get("loc") or {}).get("lat"), (d.get("loc") or {}).get("lon"),
         datetime.now().strftime("%Y-%m-%d %H:%M"),
         (d.get("promo") or "").upper(), int(d.get("discount", 0)),
         int(d.get("discount_pct", 0)), int(d.get("prepay", 0))))
    oid = cur.lastrowid
    con.commit()
    con.close()
    return oid


def get_order(oid):
    con = db()
    row = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    con.close()
    return dict(row) if row else None


def set_status(oid, st):
    con = db()
    con.execute("UPDATE orders SET status=? WHERE id=?", (st, oid))
    con.commit()
    con.close()


def save_msgs(oid, msgs):
    con = db()
    con.execute("UPDATE orders SET msgs=? WHERE id=?", (json.dumps(msgs), oid))
    con.commit()
    con.close()


def list_orders(limit=10):
    con = db()
    rows = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def stats():
    con = db()
    today = datetime.now().strftime("%Y-%m-%d")
    tot = con.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM orders").fetchone()
    tdy = con.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ?",
                      (today + "%",)).fetchone()
    by = con.execute("SELECT status, COUNT(*) FROM orders GROUP BY status").fetchall()
    con.close()
    return {"count": tot[0], "sum": tot[1], "today_count": tdy[0], "today_sum": tdy[1],
            "by": {r[0]: r[1] for r in by}}


# ---------- Promokodlar (faqat % li) ----------
def add_promo(code, pct, max_uses=0):
    code = (code or "").strip().upper()
    if not (3 <= len(code) <= 20 and code.replace("-", "").replace("_", "").isalnum()):
        return {"ok": False, "error": "kod 3-20 belgi (harf/raqam) bo'lsin"}
    if not (1 <= pct <= 90):
        return {"ok": False, "error": "foiz 1-90 oralig'ida bo'lsin"}
    con = db()
    try:
        con.execute("INSERT OR REPLACE INTO promos(code,pct,max_uses,used,active,created_at)"
                    "VALUES(?,?,?,?,1,?)",
                    (code, pct, max_uses, 0, datetime.now().strftime("%Y-%m-%d %H:%M")))
        con.commit()
    finally:
        con.close()
    return {"ok": True, "code": code, "pct": pct}


def del_promo(code):
    con = db()
    cur = con.execute("DELETE FROM promos WHERE code=?", ((code or "").strip().upper(),))
    con.commit()
    n = cur.rowcount
    con.close()
    return n > 0


def list_promos():
    con = db()
    rows = con.execute("SELECT * FROM promos ORDER BY created_at DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def check_promo(code):
    """Promokod yaroqlimi? -> {ok, pct} / {ok:False, error}"""
    code = (code or "").strip().upper()
    if not code:
        return {"ok": False, "error": "kod kiritilmagan"}
    con = db()
    row = con.execute("SELECT * FROM promos WHERE code=?", (code,)).fetchone()
    con.close()
    if not row:
        return {"ok": False, "error": "bunday promokod yo'q"}
    d = dict(row)
    if not d["active"]:
        return {"ok": False, "error": "promokod o'chirilgan"}
    if d["max_uses"] and d["used"] >= d["max_uses"]:
        return {"ok": False, "error": "promokod tugagan"}
    return {"ok": True, "code": code, "pct": d["pct"]}


def use_promo(code):
    con = db()
    con.execute("UPDATE promos SET used = used + 1 WHERE code=?", ((code or "").strip().upper(),))
    con.commit()
    con.close()


# ---------- Mahsulotlar ----------
def _img_field(d):
    """Rasmlar ro'yxatini (yoki bitta) JSON qilib qaytaradi."""
    imgs = d.get("images")
    if not imgs and d.get("img"):
        imgs = [d["img"]]
    return json.dumps(imgs or [], ensure_ascii=False)


def _parse_imgs(raw):
    raw = raw or ""
    if raw.startswith("["):
        try:
            return [x for x in json.loads(raw) if x]
        except Exception:
            return []
    return [raw] if raw else []


def product_add(d):
    con = db()
    cur = con.execute(
        """INSERT INTO products(name,cat,price,old,material,sizes,colors,stock,descr,care,tag,img,active,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
        (d.get("name", ""), d.get("cat", "kiyimlar"), int(d.get("price", 0) or 0),
         int(d.get("old", 0) or 0), d.get("material", ""), d.get("sizes", ""),
         d.get("colors", ""), int(d.get("stock", 10) or 10), d.get("descr", ""),
         d.get("care", ""), d.get("tag", ""), _img_field(d),
         datetime.now().strftime("%Y-%m-%d %H:%M")))
    pid = cur.lastrowid
    con.commit()
    con.close()
    return pid


def product_get(pid):
    con = db()
    row = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    con.close()
    return dict(row) if row else None


def product_list(active_only=True):
    con = db()
    q = "SELECT * FROM products" + (" WHERE active=1" if active_only else "") + " ORDER BY id DESC"
    rows = con.execute(q).fetchall()
    con.close()
    return [dict(r) for r in rows]


def product_del(pid):
    con = db()
    cur = con.execute("DELETE FROM products WHERE id=?", (pid,))
    con.commit()
    n = cur.rowcount
    con.close()
    return n > 0


def public_product(r):
    """Bazadagi mahsulotni sayt kutgan ko'rinishga o'girish."""
    srcs = []
    for i, e in enumerate(_parse_imgs(r.get("img"))):
        srcs.append(e[4:] if e.startswith("url:") else f"/api/img/{r['id']}/{i}")
    return {
        "id": 1000 + int(r["id"]), "name": r.get("name", ""), "cat": r.get("cat", "kiyimlar"),
        "price": int(r.get("price") or 0), "old": int(r.get("old") or 0) or None,
        "tag": r.get("tag") or None, "material": r.get("material") or "\u2014",
        "sizes": [x.strip() for x in (r.get("sizes") or "").split(",") if x.strip()],
        "colors": [x.strip() for x in (r.get("colors") or "").split(",") if x.strip()],
        "stock": int(r.get("stock") or 10), "desc": r.get("descr") or "",
        "care": r.get("care") or "Ko'rsatma yo'q", "rating": 5, "reviews": 0,
        "img": srcs[0] if srcs else "", "images": srcs,
    }


# ---------- Sozlamalar (kv) ----------
def kv_get(k, default=""):
    con = db()
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    con.close()
    return row["v"] if row else default


def kv_set(k, v):
    con = db()
    con.execute("INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)", (k, v))
    con.commit()
    con.close()


# ---------- Xabar matni + tugmalar ----------
def order_text(o):
    items = json.loads(o["items"]) if isinstance(o["items"], str) else (o["items"] or [])
    lines = [f"{i + 1}. {esc(it.get('name'))} — {it.get('qty')} × {fmt(it.get('price'))} = "
             f"{fmt((it.get('price') or 0) * (it.get('qty') or 0))}" for i, it in enumerate(items)]
    loc_line = ""
    if o.get("lat") is not None and o.get("lon") is not None:
        loc_line = (f"🗺 Lokatsiya: <a href=\"https://maps.google.com/?q={o['lat']},{o['lon']}\">"
                    f"{o['lat']}, {o['lon']}</a>\n")
    promo_line = ""
    if o.get("promo"):
        promo_line = f"🎟 Promo: <b>{esc(o['promo'])}</b> (-{o.get('discount_pct') or '?'}%)\n"
    prepay_line = ""
    if o.get("prepay"):
        prepay_line = (f"💳 Oldindan 50%: <b>{fmt(o['prepay'])}</b>\n"
                       f"💵 Qolgan (yetkazishda): <b>{fmt((o.get('total') or 0) - o['prepay'])}</b>\n")
    return (
        f"🛍 <b>Buyurtma {esc(o.get('no'))}</b>  #{o['id']}\n"
        f"{STATUS.get(o.get('status', 'new'), '')}\n"
        f"📦 Manba: {esc(o.get('source'))}\n\n"
        f"👤 Mijoz: {esc(o.get('name'))}\n"
        f"📞 Telefon: {esc(o.get('phone'))}\n"
        f"{('✉️ Email: ' + esc(o.get('email')) + chr(10)) if o.get('email') else ''}"
        f"📍 Manzil: {esc(o.get('address'))}\n"
        f"{loc_line}"
        f"🚚 Yetkazib berish: {esc(o.get('ship'))}\n"
        f"💳 To'lov: {esc(o.get('pay'))}\n"
        f"📝 Izoh: {esc(o.get('note') or '—')}\n\n"
        f"🧾 Tarkib:\n" + "\n".join(lines) + "\n\n"
        f"🧮 Mahsulotlar: {fmt(o.get('subtotal'))}\n"
        f"{('🎟 Chegirma: -' + fmt(o.get('discount')) + chr(10)) if o.get('discount') else ''}"
        f"🚚 Yetkazish: {fmt(o.get('ship_cost')) if o.get('ship_cost') else 'Bepul'}\n"
        f"💰 <b>Jami: {fmt(o.get('total'))}</b>\n"
        f"{promo_line}{prepay_line}")


def order_keyboard(oid, status):
    if status in ("delivered", "closed", "cancelled", "rejected"):
        return None
    if status == "awaiting_payment":
        return {"inline_keyboard": [
            [{"text": "❌ Bekor qilish", "callback_data": f"order:{oid}:cancelled"}],
            [{"text": "📋 Ro'yxat", "callback_data": "orders:10"}],
        ]}
    rows = []
    if status in ("awaiting_confirm",):
        rows.append([
            {"text": "✅ Chekni tasdiqlash", "callback_data": f"order:{oid}:accepted"},
            {"text": "❌ Rad etish", "callback_data": f"order:{oid}:rejected"},
        ])
    elif status == "new":
        rows.append([
            {"text": "✅ Qabul qilish", "callback_data": f"order:{oid}:accepted"},
            {"text": "❌ Rad etish", "callback_data": f"order:{oid}:cancelled"},
        ])
    else:
        rows.append([
            {"text": "🟡 Tayyorlanmoqda", "callback_data": f"order:{oid}:preparing"},
            {"text": "🚚 Yo'lda", "callback_data": f"order:{oid}:delivering"},
        ])
        rows.append([
            {"text": "🏁 Yetkazildi", "callback_data": f"order:{oid}:delivered"},
            {"text": "❌ Bekor", "callback_data": f"order:{oid}:cancelled"},
        ])
    rows.append([{"text": "📋 Ro'yxat", "callback_data": "orders:10"}])
    return {"inline_keyboard": rows}


def notify_admins(oid):
    """Yangi buyurtmani adminlarga tugmalar bilan yuborish. msgs saqlanadi."""
    o = get_order(oid)
    if not o:
        return []
    kb = order_keyboard(oid, o["status"])
    sent = []
    for admin in ADMIN_IDS:
        r = tg("sendMessage", {"chat_id": admin, "text": order_text(o),
                               "parse_mode": "HTML",
                               "reply_markup": kb} if kb else
                             {"chat_id": admin, "text": order_text(o), "parse_mode": "HTML"})
        if r.get("ok"):
            sent.append({"chat": admin, "msg": r["result"]["message_id"]})
        if o.get("lat") is not None and o.get("lon") is not None:
            tg("sendLocation", {"chat_id": admin, "latitude": o["lat"], "longitude": o["lon"]})
    if sent:
        save_msgs(oid, sent)
    return sent


def refresh_order_msgs(oid):
    o = get_order(oid)
    if not o:
        return
    kb = order_keyboard(oid, o["status"])
    for m in json.loads(o.get("msgs") or "[]"):
        payload = {"chat_id": m["chat"], "message_id": m["msg"],
                   "text": order_text(o), "parse_mode": "HTML"}
        if kb:
            payload["reply_markup"] = kb
        tg("editMessageText", payload)


def link_user(oid, tg_user):
    con = db()
    con.execute("UPDATE orders SET tg_user=? WHERE id=?", (tg_user, oid))
    con.commit()
    con.close()


def user_pending_order(tg_user):
    con = db()
    row = con.execute("SELECT * FROM orders WHERE tg_user=? AND status='awaiting_payment'"
                      " ORDER BY id DESC LIMIT 1", (tg_user,)).fetchone()
    con.close()
    return dict(row) if row else None


def set_check(oid, file_id):
    con = db()
    con.execute("UPDATE orders SET check_file=?, status='awaiting_confirm' WHERE id=?",
                (file_id, oid))
    con.commit()
    con.close()


def payment_instructions(o):
    card = kv_get("pay_card")
    digits = re.sub(r"\D", "", card) if card else ""
    pretty = " ".join(digits[i:i + 4] for i in range(0, len(digits), 4)) if digits else ""
    sep = "━━━━━━━━━━━━━━━━━━━━"
    if card:
        card_block = ("💳 <b>KARTA RAQAMI</b>  <i>(bosing — nusxa olinadi)</i>\n"
                      f"<pre>{esc(pretty or card)}</pre>")
    else:
        card_block = "💳 Karta raqamini operatorimiz shu chatga yuboradi."
    return (
        f"🧾 <b>Buyurtma {esc(o.get('no'))}</b>\n"
        f"{sep}\n"
        "❗️ <b>DIQQAT!</b> Buyurtmani tasdiqlash uchun <b>50% oldindan to'lov</b> qiling.\n\n"
        f"💰 Jami: {fmt(o.get('total'))}\n"
        f"💵 <b>TO'LANADI: {fmt(o.get('prepay'))}</b>\n"
        f"{sep}\n"
        f"{card_block}\n"
        f"{sep}\n"
        "📸 To'lov chekini shu chatga <b>rasm</b> qilib yuboring.\n"
        "✅ Chek tasdiqlangach, buyurtma adminga o'tadi.")


def notify_user(oid, text, kb=None):
    o = get_order(oid)
    if not o or not o.get("tg_user"):
        return False
    payload = {"chat_id": o["tg_user"], "text": text, "parse_mode": "HTML"}
    if kb:
        payload["reply_markup"] = kb
    return tg("sendMessage", payload).get("ok", False)


def user_status_text(o):
    return (f"📦 <b>Buyurtma {esc(o.get('no'))}</b>\n"
            f"{STATUS.get(o.get('status'), '')}\n"
            f"💰 Jami: <b>{fmt(o.get('total'))}</b>")


def notify_check(oid, from_chat, msg_id):
    """Chek kelganini adminlarga yuborish: foto forward + tugmali matn + lokatsiya."""
    o = get_order(oid)
    if not o:
        return []
    kb = order_keyboard(oid, o["status"])
    sent = []
    for admin in ADMIN_IDS:
        tg("forwardMessage", {"chat_id": admin, "from_chat_id": from_chat, "message_id": msg_id})
        r = tg("sendMessage", {"chat_id": admin, "text": order_text(o),
                               "parse_mode": "HTML",
                               **({"reply_markup": kb} if kb else {})})
        if r.get("ok"):
            sent.append({"chat": admin, "msg": r["result"]["message_id"]})
        if o.get("lat") is not None and o.get("lon") is not None:
            tg("sendLocation", {"chat_id": admin, "latitude": o["lat"], "longitude": o["lon"]})
    if sent:
        save_msgs(oid, sent)
    return sent


# ---------- Mahsulot qo'shish wizardi (faqat admin) ----------
ADD_FLOW = {}  # chat_id -> {"step": int, "data": dict}

PRODUCT_STEPS = [
    ("name", "1/9 — Mahsulot nomini yozing:"),
    ("cat", "2/9 — Kategoriyani tanlang:"),
    ("price", "3/9 — Narxini yozing (so'm). Faqat raqam, masalan: 189000"),
    ("old", "4/9 — Eski narxi (chegirma uchun) yoki «-» o'tkazib yuborish:"),
    ("sizes", "5/9 — O'lchamlar, vergul bilan (S,M,L,XL) yoki «-»:"),
    ("colors", "6/9 — Ranglar, vergul bilan (Oq,Qora) yoki «-»:"),
    ("material", "7/9 — Material yoki «-»:"),
    ("desc", "8/9 — Qisqa tavsif yoki «-»:"),
    ("photos", "9/9 — Mahsulot rasmlarini yuboring (1 tadan 4 tagacha). Bo'lgach «tayyor» deb yozing, o'tkazib yuborish uchun «-»:"),
]


def padd_start(chat, sender):
    ADD_FLOW[chat] = {"step": 0, "data": {}}
    padd_prompt(chat, sender)


def padd_prompt(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    key, prompt = PRODUCT_STEPS[st["step"]]
    if key == "cat":
        sender["send"](chat, prompt, {"inline_keyboard": [
            [{"text": "👕 Kiyimlar", "callback_data": "padd:cat:kiyimlar"}],
            [{"text": "👜 Aksessuarlar", "callback_data": "padd:cat:aksessuarlar"}],
            [{"text": "❌ Bekor qilish", "callback_data": "padd:cancel"}],
        ]})
    else:
        sender["send"](chat, prompt + "\n\n<i>/cancel — bekor qilish</i>")


def padd_store(chat, key, raw):
    d = ADD_FLOW[chat]["data"]
    raw = (raw or "").strip()
    if key == "name":
        if not raw:
            return "⛔ Nom bo'sh bo'lmasin."
        d["name"] = raw
    elif key == "price":
        num = re.sub(r"\D", "", raw)
        if not num or int(num) <= 0:
            return "⛔ Narx faqat raqam bo'lsin."
        d["price"] = int(num)
    elif key == "old":
        if raw in ("-", "", "yo'q"):
            d["old"] = 0
        else:
            num = re.sub(r"\D", "", raw)
            if not num:
                return "⛔ Eski narx raqam yoki «-» bo'lsin."
            d["old"] = int(num)
    elif key in ("sizes", "colors"):
        d[key] = "" if raw == "-" else raw.replace(";", ",")
    elif key == "material":
        d["material"] = "" if raw == "-" else raw
    elif key == "desc":
        d["descr"] = "" if raw == "-" else raw
    return ""


def padd_advance(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    st["step"] += 1
    if st["step"] >= len(PRODUCT_STEPS):
        padd_confirm(chat, sender)
    else:
        padd_prompt(chat, sender)


def padd_input(chat, raw, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    key = PRODUCT_STEPS[st["step"]][0]
    err = padd_store(chat, key, raw)
    if err:
        sender["send"](chat, err)
        return
    padd_advance(chat, sender)


def padd_confirm(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    d = st["data"]
    nimg = len(d.get("images") or ([] if not d.get("img") else [d["img"]]))
    has_img = f"✅ {nimg} ta" if nimg else "— yo'q"
    sender["send"](chat,
        "🧾 <b>Yangi mahsulot</b>\n\n"
        f"Nom: <b>{esc(d.get('name'))}</b>\n"
        f"Kategoriya: {esc(d.get('cat'))}\n"
        f"Narx: {fmt(d.get('price'))}\n"
        f"Eski narx: {fmt(d.get('old')) if d.get('old') else '—'}\n"
        f"O'lchamlar: {esc(d.get('sizes') or '—')}\n"
        f"Ranglar: {esc(d.get('colors') or '—')}\n"
        f"Material: {esc(d.get('material') or '—')}\n"
        f"Tavsif: {esc(d.get('descr') or '—')}\n"
        f"Rasm: {has_img}\n\n"
        "Saqlaymizmi?",
        {"inline_keyboard": [
            [{"text": "✅ Saqlash", "callback_data": "padd:save"},
             {"text": "❌ Bekor", "callback_data": "padd:cancel"}],
        ]})


def padd_save(chat, sender):
    st = ADD_FLOW.pop(chat, None)
    if not st:
        return
    d = st["data"]
    pid = product_add(d)
    sender["send"](chat,
        f"✅ <b>{esc(d.get('name'))}</b> qo'shildi! (ID #{pid})\n"
        "Endi u saytda ko'rinadi (do'kon, bosh sahifa).\n\n"
        "➕ Yana qo'shish: /addproduct\n📦 Ro'yxat: /products")


def padd_cancel(chat, sender):
    if ADD_FLOW.pop(chat, None):
        sender["send"](chat, "❌ Mahsulot qo'shish bekor qilindi.")
    else:
        sender["send"](chat, "ℹ️ Faol wizard yo'q.")


def padd_handle_message(chat, msg, text, sender):
    """Wizard faol bo'lsa xabarni qayta ishlaydi. True — yutilgan (boshqa handlerlarga o'tmaydi)."""
    st = ADD_FLOW.get(chat)
    if not st:
        return False
    if text.lower() in ("/cancel", "/bekor", "bekor"):
        padd_cancel(chat, sender)
        return True
    if text.startswith("/"):
        ADD_FLOW.pop(chat, None)
        sender["send"](chat, "ℹ️ Mahsulot qo'shish to'xtatildi.")
        return False
    key = PRODUCT_STEPS[st["step"]][0]
    photos = msg.get("photo") or []
    doc = msg.get("document") or {}
    fid = (photos[-1].get("file_id") if photos else None) or doc.get("file_id")
    if key == "cat":
        sender["send"](chat, "👆 Kategoriyani yuqoridagi tugmalardan tanlang.")
        padd_prompt(chat, sender)
        return True
    if key == "photos":
        imgs = st["data"].setdefault("images", [])
        if text.lower() in ("tayyor", "ok", "tamom", "done", "bo'ldi"):
            if not imgs:
                sender["send"](chat, "❗️ Kamida 1 ta rasm yuboring yoki «-» deb o'tkazib yuboring.")
                return True
            padd_advance(chat, sender)
            return True
        if text == "-":
            padd_advance(chat, sender)
            return True
        if fid:
            if len(imgs) >= 4:
                sender["send"](chat, "❗️ Maksimal 4 ta rasm. «tayyor» deb yozing.")
                return True
            imgs.append("tg:" + fid)
        elif text:
            for u in text.split():
                if len(imgs) < 4:
                    imgs.append("url:" + u)
        else:
            sender["send"](chat, "📸 Rasmni foto qilib yuboring, URL yozing yoki «tayyor» deb yozing.")
            return True
        if len(imgs) >= 4:
            sender["send"](chat, "✅ 4/4 rasm qabul qilindi.")
            padd_advance(chat, sender)
        else:
            sender["send"](chat, f"✅ {len(imgs)}/4 rasm. Yana yuboring yoki «tayyor» deb yozing.")
        return True
    if not text:
        sender["send"](chat, "✍️ Iltimos, matn ko'rinishida yozing.")
        return True
    padd_input(chat, text, sender)
    return True


def send_products_admin(chat, sender):
    ps = product_list(active_only=False)
    if not ps:
        sender["send"](chat, "📦 Hozircha mahsulot yo'q.\n➕ Qo'shish: /addproduct")
        return
    lines, kb = [], []
    for p in ps:
        off = "" if p.get("active", 1) else " (o'chirilgan)"
        lines.append(f"#{p['id']} <b>{esc(p['name'])}</b> — {fmt(p['price'])} · {esc(p['cat'])}{off}")
        kb.append([{"text": f"🗑 #{p['id']} {p['name'][:22]}", "callback_data": f"pdel:{p['id']}"}])
    sender["send"](chat, "📦 <b>Mahsulotlar:</b>\n\n" + "\n".join(lines) + "\n\n➕ /addproduct",
                   {"inline_keyboard": kb})


# ---------- Update'larni qayta ishlash (test uchun ajratilgan) ----------
def process_update(u, sender):
    """sender: dict(send(chat,text,kb), edit(chat,msg,text,kb), answer(qid,text), loc(chat,lat,lon))."""
    if "callback_query" in u:
        q = u["callback_query"]
        from_id = q["from"]["id"]
        data = q.get("data", "")

        # Mijozning "Qabul qildim" tugmasi (admin bo'lishi shart emas)
        if data.startswith("recv:"):
            oid = int(data.split(":")[1])
            o = get_order(oid)
            if not o or o.get("status") != "delivered":
                sender["answer"](q["id"], "Buyurtma topilmadi")
                return
            if o.get("tg_user") != from_id:
                sender["answer"](q["id"], "Ruxsat yo'q ⛔")
                return
            set_status(oid, "closed")
            refresh_order_msgs(oid)
            sender["answer"](q["id"], "Rahmat! 🎉")
            sender["send"](from_id, f"🎉 <b>Buyurtma {esc(o['no'])} yakunlandi!</b>\nXaridingiz uchun rahmat 💚")
            for admin in ADMIN_IDS:
                sender["send"](admin, f"📦 Mijoz <b>{esc(o['no'])}</b> ni qabul qildi ✅ (yakunlandi)")
            return

        if from_id not in ADMIN_IDS:
            sender["answer"](q["id"], "Ruxsat yo'q ⛔")
            return
        # --- Mahsulot wizardi / boshqaruv ---
        if data == "products":
            sender["answer"](q["id"], "")
            send_products_admin(from_id, sender)
            return
        if data.startswith("pdel:"):
            pid = int(data.split(":")[1])
            sender["answer"](q["id"], "O'chirildi 🗑" if product_del(pid) else "Topilmadi")
            send_products_admin(from_id, sender)
            return
        if data.startswith("padd:"):
            act = data.split(":", 2)
            what = act[1] if len(act) > 1 else ""
            if what == "new":
                sender["answer"](q["id"], "")
                padd_start(from_id, sender)
            elif what == "cat":
                st = ADD_FLOW.get(from_id)
                if not st:
                    sender["answer"](q["id"], "Wizard topilmadi")
                    return
                st["data"]["cat"] = act[2] if len(act) > 2 else "kiyimlar"
                sender["answer"](q["id"], "Tanlandi ✅")
                padd_advance(from_id, sender)
            elif what == "save":
                sender["answer"](q["id"], "Saqlanmoqda...")
                padd_save(from_id, sender)
            elif what == "cancel":
                sender["answer"](q["id"], "Bekor qilindi")
                padd_cancel(from_id, sender)
            return
        if data.startswith("order:"):
            _, oid_s, action = data.split(":")
            oid = int(oid_s)
            if action in STATUS:
                prev = (get_order(oid) or {}).get("status")
                set_status(oid, action)
                refresh_order_msgs(oid)
                sender["answer"](q["id"], STATUS[action])
                # Mijozga bildirish
                if action == "accepted" and prev == "awaiting_confirm":
                    notify_user(oid, f"✅ <b>To'lov tasdiqlandi!</b>\n{user_status_text(get_order(oid))}\n⏳ Tayyorlanmoqda, kuting.")
                elif action == "rejected":
                    notify_user(oid, f"❌ <b>Buyurtma rad etildi.</b>\n{user_status_text(get_order(oid))}\n"
                                     "Chek tasdiqlanmadi yoki xato topildi. Operatorimiz bog'lanadi.")
                elif action == "preparing":
                    notify_user(oid, f"🟡 <b>Buyurtmangiz tayyorlanmoqda...</b>\n{user_status_text(get_order(oid))}")
                elif action == "delivering":
                    notify_user(oid, f"🚚 <b>Buyurtmangiz yo'lda!</b>\n{user_status_text(get_order(oid))}")
                elif action == "delivered":
                    notify_user(oid, f"📦 <b>Buyurtma yetkazildi!</b>\n{user_status_text(get_order(oid))}\n"
                                     "Qabul qildingizmi?",
                                     {"inline_keyboard": [[{"text": "✅ Qabul qildim", "callback_data": f"recv:{oid}"}]]})
                elif action == "cancelled":
                    notify_user(oid, f"❌ <b>Buyurtma bekor qilindi.</b>\n{user_status_text(get_order(oid))}")
            return
        if data == "orders:10":
            sender["answer"](q["id"], "")
            send_orders_list(from_id, sender)
            return
        if data == "stats":
            sender["answer"](q["id"], "")
            send_stats(from_id, sender)
            return
        if data == "promos":
            sender["answer"](q["id"], "")
            send_promos(from_id, sender)
            return
        if data.startswith("promo_del:"):
            code = data.split(":", 1)[1]
            ok = del_promo(code)
            sender["answer"](q["id"], "O'chirildi 🗑" if ok else "Topilmadi")
            send_promos(from_id, sender)
            return
        if data.startswith("view:"):
            o = get_order(int(data.split(":")[1]))
            if o:
                sender["send"](from_id, order_text(o), order_keyboard(o["id"], o["status"]))
            sender["answer"](q["id"], "")
            return
        sender["answer"](q["id"], "")
        return

    msg = u.get("message") or {}
    chat = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat:
        return

    # --- Mahsulot qo'shish wizardi (faqat admin) ---
    if chat in ADD_FLOW and padd_handle_message(chat, msg, text, sender):
        return

    # --- Chek rasmi (foto/hujjat) — mijozdan ---
    photos = msg.get("photo") or []
    doc = msg.get("document") or {}
    file_id = (photos[-1].get("file_id") if photos else None) or doc.get("file_id")
    if file_id:
        if chat in ADMIN_IDS:
            sender["send"](chat, "ℹ️ Chekni mijoz yuboradi. Buyurtmalar: /orders")
            return
        pend = user_pending_order(chat)
        if not pend:
            sender["send"](chat, "📭 To'lov kutilayotgan buyurtmangiz topilmadi.\n"
                                 "Avval saytdan buyurtma berib, berilgan bot link orqali kiring.")
            return
        set_check(pend["id"], file_id)
        refresh_order_msgs(pend["id"])
        notify_check(pend["id"], chat, msg.get("message_id"))
        sender["send"](chat, f"✅ <b>Chek qabul qilindi!</b>\n{user_status_text(get_order(pend['id']))}\n"
                             "🔎 Admin tekshirmoqda, kuting.")
        return

    # --- /start ord_ID — buyurtma linki (hamma uchun) ---
    if text.startswith("/start"):
        parts = text.split()
        payload = parts[1] if len(parts) > 1 else ""
        if payload.startswith("ord_"):
            try:
                oid = int(payload[4:])
            except ValueError:
                oid = 0
            o = get_order(oid) if oid else None
            if not o:
                sender["send"](chat, "⛔ Buyurtma topilmadi.")
                return
            if o.get("status") not in ("awaiting_payment",):
                sender["send"](chat, f"{user_status_text(o)}\n\n/myorders — buyurtmalarim")
                return
            link_user(oid, chat)
            refresh_order_msgs(oid)
            sender["send"](chat, payment_instructions(get_order(oid)))
            return
        if chat in ADMIN_IDS:
            sender["send"](chat, "👋 <b>SAMA BASIC — admin panel</b>\n\n"
                                 "Buyruqlar:\n"
                                 "/orders — so'nggi buyurtmalar\n"
                                 "/stats — statistika\n"
                                 "/addproduct — yangi mahsulot qo'shish\n"
                                 "/products — mahsulotlar ro'yxati\n"
                                 "/promo_add KOD FOIZ [SONI] — promokod yaratish\n"
                                 "/setcard KARTA — oldindan to'lov kartasi\n"
                                 "/help — yordam",
                           {"inline_keyboard": [
                               [{"text": "📋 Buyurtmalar", "callback_data": "orders:10"}],
                               [{"text": "➕ Mahsulot qo'shish", "callback_data": "padd:new"},
                                {"text": "📦 Mahsulotlar", "callback_data": "products"}],
                               [{"text": "📊 Statistika", "callback_data": "stats"},
                                {"text": "🎟 Promokodlar", "callback_data": "promos"}],
                           ]})
            return
        sender["send"](chat, "👋 <b>SAMA BASIC</b> do'kon boti.\n\n"
                             "Buyurtma berish uchun saytdan buyurtma qoldiring — "
                             "to'lov uchun shu botga link beriladi.\n\n"
                             "/myorders — buyurtmalarim")
        return

    # --- /myorders — mijozning buyurtmalari ---
    if text.startswith("/myorders"):
        con = db()
        rows = con.execute("SELECT * FROM orders WHERE tg_user=? ORDER BY id DESC LIMIT 5",
                           (chat,)).fetchall()
        con.close()
        if not rows:
            sender["send"](chat, "📭 Buyurtmalaringiz topilmadi.")
            return
        kb = []
        lines = []
        for r in rows:
            d = dict(r)
            lines.append(f"{STATUS.get(d['status'], '')} <b>{esc(d['no'])}</b> — <b>{fmt(d['total'])}</b>")
            if d["status"] == "delivered":
                kb.append([{"text": f"✅ Qabul qildim ({d['no']})", "callback_data": f"recv:{d['id']}"}])
        sender["send"](chat, "📦 <b>Buyurtmalarim:</b>\n\n" + "\n".join(lines),
                       {"inline_keyboard": kb} if kb else None)
        return

    if chat not in ADMIN_IDS:
        sender["send"](chat, "ℹ️ Buyurtma uchun saytdan foydalaning.\n/myorders — buyurtmalarim")
        return
    if text.startswith("/panel"):
        sender["send"](chat, "👋 <b>SAMA BASIC — admin panel</b>\n\n"
                             "/orders — buyurtmalar\n"
                             "/addproduct — mahsulot qo'shish\n"
                             "/products — mahsulotlar\n"
                             "/stats — statistika\n"
                             "/promo_list — promokodlar",
                       {"inline_keyboard": [
                           [{"text": "📋 Buyurtmalar", "callback_data": "orders:10"}],
                           [{"text": "➕ Mahsulot qo'shish", "callback_data": "padd:new"},
                            {"text": "📦 Mahsulotlar", "callback_data": "products"}],
                           [{"text": "📊 Statistika", "callback_data": "stats"},
                            {"text": "🎟 Promokodlar", "callback_data": "promos"}],
                       ]})
    elif text.startswith("/orders"):
        send_orders_list(chat, sender)
    elif text.startswith("/stats"):
        send_stats(chat, sender)
    elif text.startswith("/addproduct") or text.startswith("/mahsulot"):
        padd_start(chat, sender)
    elif text.startswith("/products") or text.startswith("/mahsulotlar"):
        send_products_admin(chat, sender)
    elif text.startswith("/delproduct") or text.startswith("/mahsulot_del"):
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            sender["send"](chat, "♻️ Format: <code>/delproduct ID</code> (ID ni /products dan ko'ring)")
            return
        sender["send"](chat, "🗑 O'chirildi." if product_del(int(parts[1])) else "⛔ Topilmadi.")
    elif text.startswith("/promo_add"):
        parts = text.split()
        if len(parts) < 3:
            sender["send"](chat, "♻️ Format: <code>/promo_add KOD FOIZ [SONI]</code>\n"
                                 "Masalan: <code>/promo_add SALOM10 10 50</code> — 10% li, 50 marta.")
            return
        try:
            pct = int(parts[2])
        except ValueError:
            sender["send"](chat, "⛔ Foiz butun son bo'lsin (1-90).")
            return
        lim = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        r = add_promo(parts[1], pct, lim)
        sender["send"](chat, f"✅ Promokod yaratildi: <b>{r['code']}</b> — {r['pct']}%"
                             + (f" ({lim} marta)" if lim else " (cheksiz)") if r["ok"]
                       else f"⛔ {r['error']}")
    elif text.startswith("/promo_list"):
        send_promos(chat, sender)
    elif text.startswith("/promo_del"):
        parts = text.split()
        if len(parts) < 2:
            sender["send"](chat, "♻️ Format: <code>/promo_del KOD</code>")
            return
        sender["send"](chat, "🗑 O'chirildi." if del_promo(parts[1]) else "⛔ Topilmadi.")
    elif text.startswith("/setcard"):
        parts = text.split()
        if len(parts) < 2:
            sender["send"](chat, "♻️ Format: <code>/setcard 8600123456789012</code>")
            return
        kv_set("pay_card", parts[1])
        sender["send"](chat, f"💳 To'lov kartasi saqlandi: <code>{esc(parts[1])}</code>")
    elif text.startswith("/card"):
        card = kv_get("pay_card")
        sender["send"](chat, f"💳 Karta: <code>{esc(card)}</code>" if card else "💳 Karta kiritilmagan. /setcard")
    elif text.startswith("/help"):
        sender["send"](chat, "ℹ️ Yangi buyurtma kelganda tugmalar bilan xabar keladi:\n"
                             "✅ Qabul — mijozga qo'ng'iroq qiling\n"
                             "🟡 → 🚚 → 🏁 — holatni yangilang\n"
                             "❌ — bekor qilingan\n\n"
                             "➕ Mahsulot qo'shish: /addproduct\n"
                             "📦 Mahsulotlar: /products · o'chirish: /delproduct ID\n"
                             "🎟 Promokod: /promo_add KOD FOIZ [SONI]\n"
                             "💳 Karta: /setcard KARTA")
    else:
        sender["send"](chat, "Noma'lum buyruq. /help ni bosing.")


def send_orders_list(chat, sender):
    orders = list_orders(10)
    if not orders:
        sender["send"](chat, "📭 Hozircha buyurtmalar yo'q.")
        return
    kb_rows = []
    lines = []
    for o in orders:
        lines.append(f"{STATUS.get(o['status'], '')} <b>{esc(o['no'])}</b> — {esc(o['name'])} — "
                     f"<b>{fmt(o['total'])}</b>")
        kb_rows.append([{"text": f"#{o['id']} {o['no']}", "callback_data": f"view:{o['id']}"}])
    # view tugmasi hozircha ro'yxat ichida ko'rsatish uchun:
    sender["send"](chat, "📋 <b>So'nggi buyurtmalar:</b>\n\n" + "\n".join(lines),
                   {"inline_keyboard": kb_rows})


def send_promos(chat, sender):
    promos = list_promos()
    if not promos:
        sender["send"](chat, "🎟 Promokodlar yo'q.\nYaratish: <code>/promo_add KOD FOIZ [SONI]</code>")
        return
    lines = []
    kb = []
    for p in promos:
        left = "cheksiz" if not p["max_uses"] else f"{p['used']}/{p['max_uses']}"
        lines.append(f"🎟 <b>{esc(p['code'])}</b> — {p['pct']}% ({left})")
        kb.append([{"text": f"❌ {p['code']}", "callback_data": f"promo_del:{p['code']}"}])
    kb.append([{"text": "📋 Ro'yxat", "callback_data": "orders:10"}])
    sender["send"](chat, "🎟 <b>Promokodlar:</b>\n\n" + "\n".join(lines), {"inline_keyboard": kb})


def send_stats(chat, sender):
    s = stats()
    by = "\n".join(f"{STATUS.get(k, k)}: <b>{v}</b>" for k, v in s["by"].items()) or "—"
    sender["send"](chat,
                   f"📊 <b>Statistika</b>\n\n"
                   f"Jami: <b>{s['count']}</b> ta — <b>{fmt(s['sum'])}</b>\n"
                   f"Bugun: <b>{s['today_count']}</b> ta — <b>{fmt(s['today_sum'])}</b>\n\n"
                   f"{by}")


def real_sender():
    return {
        "send": lambda c, t, kb=None: tg("sendMessage", {"chat_id": c, "text": t,
                                                         "parse_mode": "HTML",
                                                         **({"reply_markup": kb} if kb else {})}),
        "edit": lambda c, m, t, kb=None: tg("editMessageText", {"chat_id": c, "message_id": m,
                                                                 "text": t, "parse_mode": "HTML",
                                                                 **({"reply_markup": kb} if kb else {})}),
        "answer": lambda q, t: tg("answerCallbackQuery", {"callback_query_id": q, "text": t or ""}),
        "loc": lambda c, la, lo: tg("sendLocation", {"chat_id": c, "latitude": la, "longitude": lo}),
    }


def poll_loop():
    sender = real_sender()
    offset = 0
    print("Bot polling boshlandi...", flush=True)
    while True:
        try:
            r = tg("getUpdates", {"offset": offset, "timeout": 30}, timeout=40)
            for u in r.get("result", []):
                offset = max(offset, u["update_id"] + 1)
                try:
                    process_update(u, sender)
                except Exception as e:
                    print("update xato:", e, flush=True)
        except Exception as e:
            print("poll xato:", e, flush=True)
            time.sleep(3)


# ---------- HTTP API ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("", "/health", "/api/health"):
            self._json(200, {"ok": True, "time": datetime.now().isoformat()})
        elif path == "/api/config":
            self._json(200, {"ok": True, "prepay_pct": 50,
                             "card": kv_get("pay_card"),
                             "ship_one": 40000, "ship_free_from": 2,
                             "delivery_days": 5})
        elif path == "/api/promo":
            code = (parse_qs(urlparse(self.path).query).get("code", [""])[0] or "")
            self._json(200, check_promo(code))
        elif path == "/api/products":
            self._json(200, {"ok": True, "products": [public_product(r) for r in product_list()]})
        elif path.startswith("/api/img/"):
            rest = path[len("/api/img/"):].split("/")
            try:
                _pid = int(rest[0])
            except (ValueError, IndexError):
                _pid = None
            _idx = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else 0
            self._serve_image(_pid, _idx)
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_image(self, pid, idx=0):
        """Mahsulot rasmini qaytaradi: URL bo'lsa redirect, Telegram fayl bo'lsa proxy."""
        if pid is None:
            self.send_response(404); self._cors(); self.end_headers(); return
        p = product_get(pid)
        if not p:
            self.send_response(404); self._cors(); self.end_headers(); return
        imgs = _parse_imgs(p.get("img"))
        if idx < 0 or idx >= len(imgs):
            self.send_response(404); self._cors(); self.end_headers(); return
        img = imgs[idx]
        if img.startswith("url:"):
            self.send_response(302); self._cors()
            self.send_header("Location", img[4:])
            self.end_headers()
            return
        file_id = img[3:] if img.startswith("tg:") else img
        r = tg("getFile", {"file_id": file_id})
        if not r.get("ok"):
            self.send_response(404); self._cors(); self.end_headers(); return
        fpath = r["result"]["file_path"]
        try:
            with urllib.request.urlopen(
                    f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}", timeout=20) as fr:
                data = fr.read()
        except Exception:
            self.send_response(502); self._cors(); self.end_headers(); return
        ctype = mimetypes.guess_type(fpath)[0] or "image/jpeg"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/order":
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        try:
            ln = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(ln).decode() or "{}")
        except Exception:
            d = {}
        if not d.get("items"):
            self._json(400, {"ok": False, "error": "savat bo'sh"})
            return
        if not d.get("no"):
            d["no"] = "SB-" + str(int(time.time() * 1000))[-6:]
        # Promokod: server tasdiqlaydi, chegirmani o'zi hisoblaydi
        promo = (d.get("promo") or "").strip().upper()
        pct = 0
        if promo:
            chk = check_promo(promo)
            if not chk["ok"]:
                self._json(400, {"ok": False, "error": "Promokod: " + chk["error"]})
                return
            pct = chk["pct"]
        try:
            subtotal = int(d.get("subtotal", 0))
            ship = int(d.get("shipCost", 0))
            discount = round(subtotal * pct / 100) if pct else 0
            total = subtotal - discount + ship
            d["promo"] = promo
            d["discount"] = discount
            d["discount_pct"] = pct
            d["total"] = total
            d["prepay"] = round(total / 2)  # boshlang'ich to'lov 50%
            oid = save_order(d)
            if promo:
                use_promo(promo)
            # Eslatma: adminga xabar CHEK kelganda yuboriladi (notify_check).
            # Hozir mijoz botga o'tib 50% to'laydi:
            self._json(200, {"ok": True, "id": oid, "no": d["no"],
                             "discount": discount, "total": total,
                             "prepay": d["prepay"], "notified": 0,
                             "bot_url": f"https://t.me/{BOT_USERNAME}?start=ord_{oid}"})
        except Exception as e:
            print("order xato:", e, flush=True)
            self._json(500, {"ok": False, "error": "server xatosi"})


def main():
    init_db()
    srv = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    threading.Thread(target=poll_loop, daemon=True).start()
    print(f"API http://0.0.0.0:{HTTP_PORT} — db: {DB_PATH}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
