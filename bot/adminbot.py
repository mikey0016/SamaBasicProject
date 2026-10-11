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
DB_TYPE = os.environ.get("DB_TYPE", "sqlite").strip().lower()
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "samabasic")

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
def _mysql_conn():
    import pymysql
    return pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                           password=MYSQL_PASSWORD, database=MYSQL_DB,
                           charset="utf8mb4", autocommit=False)


class DBCursor:
    """sqlite3 va pymysql kursorlari uchun yagona o'ram — har doim dict qaytaradi."""

    def __init__(self, cur, mysql):
        self._cur = cur
        self._mysql = mysql
        self._cols = []

    def execute(self, q, p=()):
        if self._mysql:
            q = q.replace("?", "%s")
        self._cur.execute(q, p or ())
        try:
            desc = self._cur.description
        except Exception:
            desc = None
        self._cols = [d[0] for d in desc] if desc else []
        return self

    def _row(self, r):
        if r is None:
            return None
        if isinstance(r, dict):
            return dict(r)
        if self._cols:
            return dict(zip(self._cols, r))
        return dict(r)

    def fetchone(self):
        return self._row(self._cur.fetchone())

    def fetchall(self):
        return [self._row(r) for r in self._cur.fetchall()]

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return self._cur.lastrowid


class DBConn:
    def __init__(self, con, mysql):
        self._con = con
        self._mysql = mysql

    def execute(self, q, p=()):
        if self._mysql:
            return DBCursor(self._con.cursor(), True).execute(q, p)
        return DBCursor(self._con.cursor(), False).execute(q, p)

    def commit(self):
        self._con.commit()

    def close(self):
        try:
            self._con.close()
        except Exception:
            pass


def db():
    if DB_TYPE == "mysql":
        return DBConn(_mysql_conn(), True)
    return DBConn(sqlite3.connect(DB_PATH), False)


def _init_mysql(con):
    con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INT AUTO_INCREMENT PRIMARY KEY, no TEXT, source TEXT, name TEXT, phone TEXT, email TEXT,
        address TEXT, ship TEXT, pay TEXT, note TEXT,
        items TEXT, subtotal INT DEFAULT 0, ship_cost INT DEFAULT 0, total INT DEFAULT 0,
        lat DOUBLE DEFAULT NULL, lon DOUBLE DEFAULT NULL, status VARCHAR(32) DEFAULT 'new',
        msgs TEXT, created_at TEXT,
        promo TEXT DEFAULT '', discount INT DEFAULT 0, discount_pct INT DEFAULT 0,
        prepay INT DEFAULT 0, tg_user BIGINT DEFAULT 0, check_file TEXT DEFAULT '')""")
    con.execute("""CREATE TABLE IF NOT EXISTS promos(
        code VARCHAR(32) PRIMARY KEY, pct INT, max_uses INT DEFAULT 0,
        used INT DEFAULT 0, active INT DEFAULT 1, created_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS kv(k VARCHAR(64) PRIMARY KEY, v TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS products(
        id INT AUTO_INCREMENT PRIMARY KEY,
        name TEXT, cat TEXT DEFAULT 'kiyimlar', price INT DEFAULT 0, old INT DEFAULT 0,
        material TEXT DEFAULT '', sizes TEXT DEFAULT '', colors TEXT DEFAULT '',
        stock INT DEFAULT 10, descr TEXT DEFAULT '', care TEXT DEFAULT '', tag TEXT DEFAULT '',
        img TEXT DEFAULT '', color_imgs TEXT DEFAULT '', active INT DEFAULT 1, created_at TEXT)""")
    for tbl, col in (("orders", "promo TEXT"), ("orders", "discount INT DEFAULT 0"),
                     ("orders", "discount_pct INT DEFAULT 0"), ("orders", "prepay INT DEFAULT 0"),
                     ("orders", "tg_user BIGINT DEFAULT 0"), ("orders", "check_file TEXT DEFAULT ''"),
                     ("products", "color_imgs TEXT DEFAULT ''")):
        try:
            con.execute(f"ALTER TABLE {tbl} ADD COLUMN {col}")
        except Exception as e:
            print("migrate:", e, flush=True)


def init_db():
    con = db()
    if DB_TYPE == "mysql":
        _init_mysql(con)
        con.commit()
        con.close()
        return
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
        img TEXT DEFAULT '', color_imgs TEXT DEFAULT '', active INTEGER DEFAULT 1, created_at TEXT)""")
    for col in ("promo TEXT DEFAULT ''", "discount INTEGER DEFAULT 0",
                "discount_pct INTEGER DEFAULT 0", "prepay INTEGER DEFAULT 0",
                "tg_user INTEGER DEFAULT 0", "check_file TEXT DEFAULT ''"):
        try:
            con.execute(f"ALTER TABLE orders ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass
    for col in ("color_imgs TEXT DEFAULT ''",):
        try:
            con.execute(f"ALTER TABLE products ADD COLUMN {col}")
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


# ---------- Buyurtmalar ro'yxati: filtrlar + sahifalash ----------
PAGE_SIZE = 5

ORDER_FILTERS = {
    "pending": ("Kutulmoqda", ["new", "awaiting_payment", "awaiting_confirm"]),
    "accepted": ("Qabul qilingan", ["accepted", "preparing", "delivering", "delivered", "closed"]),
    "rejected": ("Rad etilgan", ["cancelled", "rejected"]),
    "all": ("Barchasi", None),
}


def count_orders(statuses=None):
    con = db()
    if statuses:
        q = "SELECT COUNT(*) AS c FROM orders WHERE status IN (%s)" % ",".join("?" * len(statuses))
        n = con.execute(q, tuple(statuses)).fetchone()["c"]
    else:
        n = con.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    con.close()
    return n


def list_orders_filtered(statuses=None, limit=5, offset=0):
    con = db()
    if statuses:
        q = ("SELECT * FROM orders WHERE status IN (%s) ORDER BY id DESC LIMIT ? OFFSET ?"
             % ",".join("?" * len(statuses)))
        rows = con.execute(q, (*statuses, limit, offset)).fetchall()
    else:
        rows = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ? OFFSET ?",
                           (limit, offset)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def stats():
    con = db()
    today = datetime.now().strftime("%Y-%m-%d")
    tot = con.execute("SELECT COUNT(*) AS c, COALESCE(SUM(total),0) AS s FROM orders").fetchone()
    tdy = con.execute("SELECT COUNT(*) AS c, COALESCE(SUM(total),0) AS s FROM orders WHERE created_at LIKE ?",
                      (today + "%",)).fetchone()
    by = con.execute("SELECT status, COUNT(*) AS n FROM orders GROUP BY status").fetchall()
    con.close()
    return {"count": tot["c"], "sum": tot["s"], "today_count": tdy["c"], "today_sum": tdy["s"],
            "by": {r["status"]: r["n"] for r in by}}


# ---------- Promokodlar (faqat % li) ----------
def add_promo(code, pct, max_uses=0):
    code = (code or "").strip().upper()
    if not (3 <= len(code) <= 20 and code.replace("-", "").replace("_", "").isalnum()):
        return {"ok": False, "error": "kod 3-20 belgi (harf/raqam) bo'lsin"}
    if not (1 <= pct <= 90):
        return {"ok": False, "error": "foiz 1-90 oralig'ida bo'lsin"}
    con = db()
    try:
        if DB_TYPE == "mysql":
            con.execute("INSERT INTO promos(code,pct,max_uses,used,active,created_at)"
                        "VALUES(?,?,?,?,1,?) ON DUPLICATE KEY UPDATE pct=VALUES(pct),"
                        "max_uses=VALUES(max_uses),used=0,active=1,created_at=VALUES(created_at)",
                        (code, pct, max_uses, 0, datetime.now().strftime("%Y-%m-%d %H:%M")))
        else:
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


def _color_img_field(d):
    """Har rang uchun alohida rasmlar: {rang: [ref, ...]} JSON."""
    ci = d.get("color_images") or {}
    clean = {c: [x for x in v if x] for c, v in ci.items() if v}
    return json.dumps(clean, ensure_ascii=False)


def _parse_color_imgs(raw):
    try:
        d = json.loads(raw or "{}")
        return {c: [x for x in v if x] for c, v in d.items() if v} if isinstance(d, dict) else {}
    except Exception:
        return {}


def product_add(d):
    con = db()
    cur = con.execute(
        """INSERT INTO products(name,cat,price,old,material,sizes,colors,stock,descr,care,tag,img,color_imgs,active,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
        (d.get("name", ""), d.get("cat", "kiyimlar"), int(d.get("price", 0) or 0),
         int(d.get("old", 0) or 0), d.get("material", ""), d.get("sizes", ""),
         d.get("colors", ""), int(d.get("stock", 10) or 10), d.get("descr", ""),
         d.get("care", ""), d.get("tag", ""), _img_field(d), _color_img_field(d),
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
        if e.startswith("url:"):
            if e[4:].startswith("http"):
                srcs.append(e[4:])
            continue
        srcs.append(f"/api/img/{r['id']}/{i}")
    cmap = _parse_color_imgs(r.get("color_imgs"))
    cg = {}
    for n, c in enumerate(sorted(cmap.keys())):
        arr = []
        for m, e in enumerate(cmap[c]):
            if e.startswith("url:"):
                if e[4:].startswith("http"):
                    arr.append(e[4:])
                continue
            arr.append(f"/api/cimg/{r['id']}/{n}/{m}")
        if arr:
            cg[c] = arr
    return {
        "id": 1000 + int(r["id"]), "name": r.get("name", ""), "cat": r.get("cat", "kiyimlar"),
        "price": int(r.get("price") or 0), "old": int(r.get("old") or 0) or None,
        "tag": r.get("tag") or None, "material": r.get("material") or "\u2014",
        "sizes": [x.strip() for x in (r.get("sizes") or "").split(",") if x.strip()],
        "colors": [x.strip() for x in (r.get("colors") or "").split(",") if x.strip()],
        "stock": int(r.get("stock") or 10), "desc": r.get("descr") or "",
        "care": r.get("care") or "Ko'rsatma yo'q", "rating": 5, "reviews": 0,
        "img": srcs[0] if srcs else "", "images": srcs, "colorGalleries": cg,
    }


# ---------- Sozlamalar (kv) ----------
def kv_get(k, default=""):
    con = db()
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    con.close()
    return row["v"] if row else default


def kv_set(k, v):
    con = db()
    if DB_TYPE == "mysql":
        con.execute("INSERT INTO kv(k,v) VALUES(?,?) ON DUPLICATE KEY UPDATE v=VALUES(v)", (k, v))
    else:
        con.execute("INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)", (k, v))
    con.commit()
    con.close()


# ---------- Xabar matni + tugmalar ----------
DIV = "━━━━━━━━━━━━"


def order_text(o):
    items = json.loads(o["items"]) if isinstance(o["items"], str) else (o["items"] or [])
    raw_lines = [f"{i + 1}. {it.get('name')} × {it.get('qty')} = "
                 f"{fmt((it.get('price') or 0) * (it.get('qty') or 0))}" for i, it in enumerate(items)]
    items_block = esc("\n".join(raw_lines)) if raw_lines else "—"
    loc_line = ""
    if o.get("lat") is not None and o.get("lon") is not None:
        loc_line = (f"🗺 <b>Xarita:</b> <a href=\"https://maps.google.com/?q={o['lat']},{o['lon']}\">"
                    f"ochish</a>\n")
    mail_line = f"✉️ <b>Email:</b> {esc(o.get('email'))}\n" if o.get("email") else ""
    promo_line = ""
    if o.get("promo"):
        promo_line = f"🎟 <b>Promo:</b> <code>{esc(o['promo'])}</code> (−{o.get('discount_pct') or '?'}%)\n"
    disc_line = f"🎟 <b>Chegirma:</b> −{fmt(o.get('discount'))}\n" if o.get("discount") else ""
    prepay_line = ""
    if o.get("prepay"):
        prepay_line = (f"\n💳 <b>Oldindan 50%:</b> <b>{fmt(o['prepay'])}</b>\n"
                       f"💵 <b>Qolgan:</b> {fmt((o.get('total') or 0) - o['prepay'])}\n")
    return (
        f"🛍 <b>Buyurtma {esc(o.get('no'))}</b> · <code>#{o['id']}</code>\n"
        f"{STATUS.get(o.get('status', 'new'), '')}\n"
        f"<i>📦 Manba: {esc(o.get('source'))}</i>\n"
        f"{DIV}\n"
        f"<b>👤 Mijoz</b>\n\n"
        f"<b>Ism:</b> {esc(o.get('name'))}\n"
        f"<b>Tel:</b> <code>{esc(o.get('phone'))}</code>\n"
        f"{mail_line}"
        f"<b>Manzil:</b> {esc(o.get('address'))}\n"
        f"{loc_line}"
        f"<b>Yetkazish:</b> {esc(o.get('ship'))}\n"
        f"<b>To'lov:</b> {esc(o.get('pay'))}\n"
        f"<b>Izoh:</b> <i>{esc(o.get('note') or '—')}</i>\n"
        f"{DIV}\n"
        f"<b>🧾 Tarkib</b>\n\n"
        f"<pre>{items_block}</pre>\n"
        f"{DIV}\n"
        f"<b>💰 Hisob</b>\n\n"
        f"Mahsulotlar: {fmt(o.get('subtotal'))}\n"
        f"{disc_line}"
        f"Yetkazish: {fmt(o.get('ship_cost')) if o.get('ship_cost') else 'Bepul'}\n"
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
        card_block = ("💳 <b><u>KARTA RAQAMI</u></b>  <i>(bosing — nusxa olinadi)</i>\n"
                      f"<pre>{esc(pretty or card)}</pre>")
    else:
        card_block = "💳 Karta raqamini operatorimiz shu chatga yuboradi."
    return (
        f"🧾 <b>Buyurtma {esc(o.get('no'))}</b>\n"
        f"{sep}\n"
        f"💰 Jami summa: {fmt(o.get('total'))}\n"
        f"💵 Oldindan to'lov — 50%:\n"
        f"<pre>{fmt(o.get('prepay'))}</pre>\n"
        f"{sep}\n"
        "⛔️ <b><u>MUHIM: Aynan yuqoridagi summani to'lang!</u></b>\n"
        "❌ <b>Ko'p ham, kam ham yubormang</b> — tiyinma-tiyin to'g'ri kelishi shart.\n"
        "<i>Noto'g'ri summa tushsa, chek tasdiqlanmaydi va buyurtmangiz kechikadi.</i>\n"
        f"{sep}\n"
        f"{card_block}\n"
        f"{sep}\n"
        "📸 <b>1-qadam:</b> To'lovni qiling.\n"
        "📸 <b>2-qadam:</b> Chekni shu chatga <b>rasm</b> qilib yuboring.\n"
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
            f"{STATUS.get(o.get('status'), '')}\n\n"
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
    ("name", "1/10 — Mahsulot nomini yozing (masalan: Oversize Futbolka):"),
    ("cat", "2/10 — Kategoriyani tanlang:"),
    ("price", "3/10 — Narxni tanlang (so'm):"),
    ("old", "4/10 — Eski narx (chegirma uchun):"),
    ("stock", "5/10 — Qoldiq sonini tanlang (dona):"),
    ("sizes", "6/10 — O'lchamlarni tanlang:"),
    ("colors", "7/10 — Ranglarni tanlang (bir nechta bo'ladi):"),
    ("material", "8/10 — Materialni tanlang:"),
    ("desc", "9/10 — Qisqa tavsif yozing:"),
    ("cphotos", "10/10 — Har bir rang uchun alohida rasm yuboring:"),
]

FIELD_LABELS = {"price": "Narx", "old": "Eski narx", "stock": "Qoldiq",
                "sizes": "O'lchamlar", "colors": "Ranglar", "material": "Material"}


def padd_start(chat, sender):
    ADD_FLOW[chat] = {"step": 0, "data": {}}
    padd_prompt(chat, sender)


def _cancel_row():
    return [{"text": "❌ Bekor qilish", "callback_data": "padd:cancel"}]


def _step_keyboard(st, key):
    """Qadam uchun inline tugmalar (None — faqat matn)."""
    if key == "cat":
        return {"inline_keyboard": [
            [{"text": "👕 Kiyimlar", "callback_data": "padd:cat:kiyimlar"}],
            [{"text": "👜 Aksessuarlar", "callback_data": "padd:cat:aksessuarlar"}],
            _cancel_row(),
        ]}
    if key == "price":
        return {"inline_keyboard": [
            [{"text": "100 000", "callback_data": "padd:set:price:100000"},
             {"text": "150 000", "callback_data": "padd:set:price:150000"},
             {"text": "200 000", "callback_data": "padd:set:price:200000"}],
            [{"text": "300 000", "callback_data": "padd:set:price:300000"},
             {"text": "500 000", "callback_data": "padd:set:price:500000"},
             {"text": "700 000", "callback_data": "padd:set:price:700000"}],
            [{"text": "✍️ Boshqa summa yozish", "callback_data": "padd:custom:price"}],
            _cancel_row(),
        ]}
    if key == "old":
        return {"inline_keyboard": [
            [{"text": "➖ Chegirmasiz", "callback_data": "padd:set:old:-"}],
            [{"text": "✍️ Eski narx yozish", "callback_data": "padd:custom:old"}],
            _cancel_row(),
        ]}
    if key == "stock":
        return {"inline_keyboard": [
            [{"text": "5", "callback_data": "padd:set:stock:5"},
             {"text": "10", "callback_data": "padd:set:stock:10"},
             {"text": "20", "callback_data": "padd:set:stock:20"},
             {"text": "50", "callback_data": "padd:set:stock:50"}],
            [{"text": "✍️ Boshqa son yozish", "callback_data": "padd:custom:stock"}],
            _cancel_row(),
        ]}
    if key == "sizes":
        return {"inline_keyboard": [
            [{"text": "S,M,L,XL", "callback_data": "padd:set:sizes:S,M,L,XL"}],
            [{"text": "S,M,L,XL,XXL", "callback_data": "padd:set:sizes:S,M,L,XL,XXL"}],
            [{"text": "28–36", "callback_data": "padd:set:sizes:28,30,32,34,36"}],
            [{"text": "One Size", "callback_data": "padd:set:sizes:One Size"}],
            [{"text": "✍️ Boshqacha yozish", "callback_data": "padd:custom:sizes"}],
            _cancel_row(),
        ]}
    if key == "colors":
        sel = st["data"].get("color_sel", [])
        palette = ["Oq", "Qora", "Olive", "Bej", "Ko'k", "Jigarrang", "Kulrang", "Krem"]
        rows = []
        for i in range(0, len(palette), 4):
            rows.append([{"text": ("✅ " if c in sel else "") + c,
                          "callback_data": f"padd:color:{c}"} for c in palette[i:i + 4]])
        rows.append([{"text": "✅ Tayyor", "callback_data": "padd:color:done"}])
        rows.append([{"text": "✍️ Ro'yxatni yozish", "callback_data": "padd:custom:colors"}])
        rows.append(_cancel_row())
        return {"inline_keyboard": rows}
    if key == "material":
        return {"inline_keyboard": [
            [{"text": "Paxta", "callback_data": "padd:set:material:Paxta"},
             {"text": "Tabiiy teri", "callback_data": "padd:set:material:Tabiiy teri"}],
            [{"text": "Jun", "callback_data": "padd:set:material:Jun"},
             {"text": "Zig'ir", "callback_data": "padd:set:material:Zig'ir"}],
            [{"text": "➖ Yo'q", "callback_data": "padd:set:material:-"}],
            [{"text": "✍️ Boshqacha yozish", "callback_data": "padd:custom:material"}],
            _cancel_row(),
        ]}
    if key == "desc":
        return {"inline_keyboard": [
            [{"text": "⏭ O'tkazib yuborish", "callback_data": "padd:set:desc:-"}],
            _cancel_row(),
        ]}
    return None


def padd_prompt(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    key, prompt = PRODUCT_STEPS[st["step"]]
    kb = _step_keyboard(st, key)
    sender["send"](chat, prompt + "\n\n<i>/cancel — bekor qilish</i>", kb)


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
    elif key == "stock":
        num = re.sub(r"\D", "", raw)
        if not num:
            return "⛔ Son noto'g'ri. Faqat raqam yuboring."
        d["stock"] = int(num)
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
    st.pop("await_custom", None)
    st["step"] += 1
    if st["step"] >= len(PRODUCT_STEPS):
        padd_confirm(chat, sender)
    elif PRODUCT_STEPS[st["step"]][0] == "cphotos":
        padd_after_photos(chat, sender)
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


def padd_after_photos(chat, sender):
    """Umumiy rasmlardan keyin har bir rang uchun alohida rasm yig'ish."""
    st = ADD_FLOW.get(chat)
    if not st:
        return
    colors = [c.strip() for c in (st["data"].get("colors") or "").split(",") if c.strip()]
    st["data"]["color_list"] = colors
    st["data"].setdefault("color_images", {})
    if colors:
        st["color_phase"] = True
        st["color_idx"] = 0
        padd_color_prompt(chat, sender)
    else:
        st["step"] = len(PRODUCT_STEPS)
        padd_confirm(chat, sender)


def padd_color_prompt(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    colors = st["data"]["color_list"]
    i = st.get("color_idx", 0)
    col = colors[i]
    have = len(st["data"]["color_images"].get(col, []))
    extra = f" — hozir {have} ta" if have else ""
    sender["send"](chat,
        f"🎨 <b>{esc(col)}</b> rangi uchun rasmlar ({i + 1}/{len(colors)}){extra}\n\n"
        "Rasmlarni <b>foto</b> qilib yuboring (1 tadan 4 tagacha). "
        "Bo'lgach «tayyor» deb yozing.\n"
        "Bu rangga rasm shart emas: «-»\n\n"
        "<i>/cancel — bekor qilish</i>")


def padd_color_next(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return True
    st["color_idx"] = st.get("color_idx", 0) + 1
    if st["color_idx"] >= len(st["data"]["color_list"]):
        total = sum(len(v) for v in st["data"].get("color_images", {}).values())
        if not total:
            st["color_idx"] = 0
            sender["send"](chat, "❗️ Kamida bitta rangga rasm yuklash shart. Qaytadan boshlaymiz:")
            padd_color_prompt(chat, sender)
            return True
        st.pop("color_phase", None)
        st.pop("color_idx", None)
        st["step"] = len(PRODUCT_STEPS)
        padd_confirm(chat, sender)
    else:
        padd_color_prompt(chat, sender)
    return True


def padd_handle_color(chat, msg, text, sender, fid):
    """Rang-bosqich xabarlari. True — yutilgan."""
    st = ADD_FLOW.get(chat)
    if not st:
        return False
    colors = st["data"]["color_list"]
    col = colors[st.get("color_idx", 0)]
    imgs = st["data"]["color_images"].setdefault(col, [])
    if text.lower() in ("tayyor", "ok", "tamom", "done", "bo'ldi"):
        if not imgs:
            sender["send"](chat, "❗️ Kamida 1 ta rasm yuboring yoki «-» deb o'tkazib yuboring.")
            return True
        return padd_color_next(chat, sender)
    if text == "-":
        st["data"]["color_images"].pop(col, None)
        return padd_color_next(chat, sender)
    if fid:
        if len(imgs) >= 4:
            sender["send"](chat, "❗️ Bu rang uchun maksimal 4 ta. «tayyor» deb yozing.")
            return True
        imgs.append("tg:" + fid)
    elif text:
        added = False
        for u in text.split():
            if len(imgs) < 4 and u.startswith("http"):
                imgs.append("url:" + u)
                added = True
        if not added and not imgs:
            sender["send"](chat, "📸 Rasmni foto qilib yuboring, URL yozing, «tayyor» yoki «-» deb yozing.")
            return True
    else:
        sender["send"](chat, "📸 Rasmni foto qilib yuboring yoki «tayyor» deb yozing.")
        return True
    if len(imgs) >= 4:
        sender["send"](chat, f"✅ {esc(col)}: 4/4 rasm qabul qilindi.")
        return padd_color_next(chat, sender)
    sender["send"](chat, f"✅ {esc(col)}: {len(imgs)}/4 rasm. Yana yuboring yoki «tayyor» deb yozing.")
    return True


def padd_confirm(chat, sender):
    st = ADD_FLOW.get(chat)
    if not st:
        return
    d = st["data"]
    sender["send"](chat,
        "🧾 <b>Yangi mahsulot</b>\n"
        f"{DIV}\n"
        f"<b>Nom:</b> {esc(d.get('name'))}\n"
        f"<b>Kategoriya:</b> {esc(d.get('cat'))}\n"
        f"<b>Narx:</b> <code>{fmt(d.get('price'))}</code>\n"
        f"<b>Eski narx:</b> {fmt(d.get('old')) if d.get('old') else '—'}\n"
        f"<b>Qoldiq:</b> {d.get('stock', 10)} dona\n"
        f"<b>O'lchamlar:</b> {esc(d.get('sizes') or '—')}\n"
        f"<b>Ranglar:</b> {esc(d.get('colors') or '—')}\n"
        f"<b>Material:</b> {esc(d.get('material') or '—')}\n"
        f"<b>Tavsif:</b> <i>{esc(d.get('descr') or '—')}</i>\n"
        f"<b>🎨 Rang rasmlari:</b>\n{(chr(10).join(f'• {esc(c)}: ✅ {len(v)} ta' for c, v in (d.get('color_images') or {}).items() if v) or '— yo‘q')}\n"
        f"{DIV}\n"
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
    if st["step"] >= len(PRODUCT_STEPS):
        return False
    if st.get("color_phase"):
        photos = msg.get("photo") or []
        doc = msg.get("document") or {}
        fid = (photos[-1].get("file_id") if photos else None) or doc.get("file_id")
        return padd_handle_color(chat, msg, text, sender, fid)
    key = PRODUCT_STEPS[st["step"]][0]
    if key == "cat":
        sender["send"](chat, "👆 Kategoriyani yuqoridagi tugmalardan tanlang.")
        padd_prompt(chat, sender)
        return True
    if st.get("await_custom"):
        field = st.pop("await_custom")
        if field == "colors":
            st["data"]["color_sel"] = []
        err = padd_store(chat, field, text)
        if err:
            st["await_custom"] = field
            sender["send"](chat, err)
            return True
        padd_advance(chat, sender)
        return True
    if key in ("price", "old", "stock", "sizes", "colors", "material"):
        # Tugma o'rniga yozib yuborilsa ham qabul qilamiz
        if key == "colors":
            st["data"]["color_sel"] = []
        err = padd_store(chat, key, text)
        if err:
            sender["send"](chat, err + "\n\nTugmalardan tanlang yoki to'g'ri yozing.")
            return True
        padd_advance(chat, sender)
        return True
    # ("photos" qadami olib tashlangan — rasmlar faqat ranglar uchun yig'iladi)
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
        st = "✅" if p.get("active", 1) else "🚫"
        lines.append(f"{st} <b>{esc(p['name'])}</b>\n"
                     f"   <code>#{p['id']}</code> · {fmt(p['price'])} · <i>{esc(p['cat'])}</i>")
        kb.append([{"text": f"🗑 #{p['id']} {p['name'][:22]}", "callback_data": f"pdel:{p['id']}"}])
    sender["send"](chat, f"📦 <b>Mahsulotlar ({len(ps)} ta)</b>\n\n" + "\n\n".join(lines)
                   + "\n\n➕ Yangi: /addproduct",
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
            elif what == "set":
                # padd:set:{maydon}:{qiymat} — qadam tugmasi
                rest = act[2] if len(act) > 2 else ""
                field, _, value = rest.partition(":")
                st = ADD_FLOW.get(from_id)
                if not st or st.get("step", 0) >= len(PRODUCT_STEPS) \
                        or PRODUCT_STEPS[st["step"]][0] != field:
                    sender["answer"](q["id"], "Eski tugma ⛔")
                    return
                if field == "colors":
                    st["data"]["color_sel"] = []
                err = padd_store(from_id, field, value)
                if err:
                    sender["answer"](q["id"], err)
                    return
                sender["answer"](q["id"], "Saqlangan ✅")
                padd_advance(from_id, sender)
            elif what == "custom":
                # padd:custom:{maydon} — qo'lda yozish
                field = act[2] if len(act) > 2 else ""
                st = ADD_FLOW.get(from_id)
                if not st or st.get("step", 0) >= len(PRODUCT_STEPS) \
                        or PRODUCT_STEPS[st["step"]][0] != field:
                    sender["answer"](q["id"], "Eski tugma ⛔")
                    return
                st["await_custom"] = field
                sender["answer"](q["id"], "")
                lbl = FIELD_LABELS.get(field, field)
                sender["send"](from_id, f"✍️ <b>{esc(lbl)}</b> ni yozib yuboring:\n\n<i>/cancel — bekor qilish</i>")
            elif what == "color":
                # padd:color:{rang} — rang tanlash, padd:color:done — tayyor
                arg = act[2] if len(act) > 2 else ""
                st = ADD_FLOW.get(from_id)
                if not st or st.get("step", 0) >= len(PRODUCT_STEPS) \
                        or PRODUCT_STEPS[st["step"]][0] != "colors":
                    sender["answer"](q["id"], "Eski tugma ⛔")
                    return
                if arg == "done":
                    sel = st["data"].get("color_sel", [])
                    if not sel:
                        sender["answer"](q["id"], "Kamida bitta rang tanlang ⛔")
                        return
                    st["data"]["colors"] = ",".join(sel)
                    sender["answer"](q["id"], "Tayyor ✅")
                    padd_advance(from_id, sender)
                    return
                sel = st["data"].setdefault("color_sel", [])
                if arg in sel:
                    sel.remove(arg)
                else:
                    sel.append(arg)
                sender["answer"](q["id"], arg)
                try:
                    mid = (q.get("message") or {}).get("message_id")
                    key, prompt = PRODUCT_STEPS[st["step"]]
                    sender["edit"](from_id, mid,
                                   prompt + "\n\n<i>/cancel — bekor qilish</i>",
                                   _step_keyboard(st, key))
                except Exception:
                    pass
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
        if data == "olist:noop":
            sender["answer"](q["id"], "Shu yerda turganmiz 👆")
            return
        if data == "orders:10" or data.startswith("orders:"):
            # Buyurtmalar ro'yxati — yangi xabar (kartochkadagi "Ro'yxat" tugmasi uchun)
            parts = data.split(":")
            filt = parts[1] if len(parts) > 2 and parts[1] in ORDER_FILTERS else "pending"
            try:
                page = int(parts[2]) if len(parts) > 2 else 0
            except ValueError:
                page = 0
            sender["answer"](q["id"], "")
            send_orders_list(from_id, sender, filt, page)
            return
        if data.startswith("olist:"):
            # Ro'yxat ichida navigatsiya — shu xabarni tahrirlash
            parts = data.split(":")
            filt = parts[1] if len(parts) > 2 and parts[1] in ORDER_FILTERS else "pending"
            try:
                page = int(parts[2]) if len(parts) > 2 else 0
            except ValueError:
                page = 0
            sender["answer"](q["id"], "")
            mid = (q.get("message") or {}).get("message_id")
            send_orders_list(from_id, sender, filt, page, edit_mid=mid)
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
            sender["send"](chat, "👋 <b>SAMA BASIC — admin panel</b>\n"
                                 f"{DIV}\n"
                                 "<b>Buyruqlar</b>\n\n"
                                 "📋 /orders — <i>so'nggi buyurtmalar</i>\n"
                                 "📊 /stats — <i>statistika</i>\n"
                                 "➕ /addproduct — <i>yangi mahsulot</i>\n"
                                 "📦 /products — <i>mahsulotlar ro'yxati</i>\n"
                                 "🎟 /promo_add KOD FOIZ [SONI] — <i>promokod</i>\n"
                                 "💳 /setcard KARTA — <i>to'lov kartasi</i>\n"
                                 "ℹ️ /help — <i>yordam</i>",
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
            lines.append(f"{STATUS.get(d['status'], '')} <b>{esc(d['no'])}</b>\n"
                         f"   💰 <b>{fmt(d['total'])}</b>")
            if d["status"] == "delivered":
                kb.append([{"text": f"✅ Qabul qildim ({d['no']})", "callback_data": f"recv:{d['id']}"}])
        sender["send"](chat, "📦 <b>Buyurtmalarim</b>\n\n" + "\n\n".join(lines),
                       {"inline_keyboard": kb} if kb else None)
        return

    if chat not in ADMIN_IDS:
        sender["send"](chat, "ℹ️ Buyurtma uchun saytdan foydalaning.\n/myorders — buyurtmalarim")
        return
    if text.startswith("/panel"):
        sender["send"](chat, "👋 <b>SAMA BASIC — admin panel</b>\n"
                             f"{DIV}\n"
                             "📋 /orders — <i>buyurtmalar</i>\n"
                             "➕ /addproduct — <i>mahsulot qo'shish</i>\n"
                             "📦 /products — <i>mahsulotlar</i>\n"
                             "📊 /stats — <i>statistika</i>\n"
                             "🎟 /promo_list — <i>promokodlar</i>",
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


def send_orders_list(chat, sender, filt="pending", page=0, edit_mid=None):
    """Buyurtmalar ro'yxati: status bo'yicha filtr + sahifalash.
    filt: pending (kutulmoqda) / accepted (qabul) / rejected (rad) / all.
    edit_mid berilsa o'sha xabar tahrirlanadi, aks holda yangi xabar yuboriladi."""
    if filt not in ORDER_FILTERS:
        filt = "pending"
    label, statuses = ORDER_FILTERS[filt]
    total = count_orders(statuses)
    maxpage = max(0, (total - 1) // PAGE_SIZE)
    page = max(0, min(page, maxpage))
    orders = list_orders_filtered(statuses, PAGE_SIZE, page * PAGE_SIZE)

    counts = {k: count_orders(v) for k, (_, v) in ORDER_FILTERS.items() if k != "all"}
    counts["all"] = count_orders(None)

    def _tab(key, title):
        if filt == key:
            return {"text": f"● {title} ({counts[key]})", "callback_data": "olist:noop"}
        return {"text": f"{title} ({counts[key]})", "callback_data": f"olist:{key}:0"}

    tabs = [[_tab("pending", "⏳ Kutulmoqda"), _tab("accepted", "✅ Qabul")],
            [_tab("rejected", "❌ Rad"), _tab("all", "📋 Barchasi")]]
    head = (f"📋 <b>Buyurtmalar · {label}</b>\n"
            f"<i>Jami: {total} ta · Sahifa {page + 1}/{maxpage + 1}</i>")
    if not orders:
        sender["send"](chat, head + "\n\n📭 Bu bo'limda buyurtma yo'q.",
                       {"inline_keyboard": tabs})
        return
    lines, kb_rows = [], []
    for o in orders:
        lines.append(f"{STATUS.get(o['status'], '')} <b>{esc(o['no'])}</b>\n"
                     f"   👤 {esc(o['name'])} · 💰 <b>{fmt(o['total'])}</b> · <code>#{o['id']}</code>")
        kb_rows.append([{"text": f"#{o['id']} {o['no']}", "callback_data": f"view:{o['id']}"}])
    nav = []
    if page > 0:
        nav.append({"text": "⬅️ Oldingi", "callback_data": f"olist:{filt}:{page - 1}"})
    nav.append({"text": f"· {page + 1}/{maxpage + 1} ·", "callback_data": "olist:noop"})
    if (page + 1) * PAGE_SIZE < total:
        nav.append({"text": "Keyingi ➡️", "callback_data": f"olist:{filt}:{page + 1}"})
    text = head + "\n\n" + "\n\n".join(lines)
    kb = {"inline_keyboard": tabs + kb_rows + [nav]}
    if edit_mid:
        try:
            r = sender["edit"](chat, edit_mid, text, kb)
            if isinstance(r, dict) and r.get("ok"):
                return
        except Exception:
            pass
    sender["send"](chat, text, kb)


def send_promos(chat, sender):
    promos = list_promos()
    if not promos:
        sender["send"](chat, "🎟 Promokodlar yo'q.\nYaratish: <code>/promo_add KOD FOIZ [SONI]</code>")
        return
    lines = []
    kb = []
    for p in promos:
        left = "cheksiz" if not p["max_uses"] else f"{p['used']}/{p['max_uses']}"
        lines.append(f"🎟 <code>{esc(p['code'])}</code> — <b>{p['pct']}%</b> <i>({left})</i>")
        kb.append([{"text": f"❌ {p['code']}", "callback_data": f"promo_del:{p['code']}"}])
    kb.append([{"text": "📋 Ro'yxat", "callback_data": "orders:10"}])
    sender["send"](chat, "🎟 <b>Promokodlar</b>\n\n" + "\n".join(lines), {"inline_keyboard": kb})


def send_stats(chat, sender):
    s = stats()
    by = "\n".join(f"{STATUS.get(k, k)} — <b>{v} ta</b>" for k, v in s["by"].items()) or "—"
    sender["send"](chat,
                   f"📊 <b>Statistika</b>\n\n"
                   f"📦 <b>Jami</b>\n{s['count']} ta · <b>{fmt(s['sum'])}</b>\n\n"
                   f"📅 <b>Bugun</b>\n{s['today_count']} ta · <b>{fmt(s['today_sum'])}</b>\n"
                   f"{DIV}\n"
                   f"<b>Holatlar bo'yicha</b>\n\n"
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
        elif path == "/api/order":
            # Buyurtma holatini tekshirish (sayt to'lov tasdiqlangach ekranni yangilaydi)
            qs = parse_qs(urlparse(self.path).query)
            try:
                _oid = int((qs.get("id", [""])[0] or ""))
            except ValueError:
                _oid = 0
            _o = get_order(_oid) if _oid else None
            if not _o:
                self._json(404, {"ok": False, "error": "buyurtma topilmadi"})
            else:
                self._json(200, {"ok": True, "id": _o["id"], "no": _o["no"],
                                 "status": _o["status"], "total": _o["total"],
                                 "prepay": _o["prepay"]})
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
        elif path.startswith("/api/cimg/"):
            rest = path[len("/api/cimg/"):].split("/")
            try:
                _pid = int(rest[0])
            except (ValueError, IndexError):
                _pid = None
            _n = int(rest[1]) if len(rest) > 1 and rest[1].isdigit() else -1
            _m = int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else -1
            self._serve_cimg(_pid, _n, _m)
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
        self._serve_ref(imgs[idx])

    def _serve_cimg(self, pid, n, m):
        """Rang rasmini qaytaradi: /api/cimg/{pid}/{rang_index}/{rasm_index}."""
        if pid is None:
            self.send_response(404); self._cors(); self.end_headers(); return
        p = product_get(pid)
        if not p:
            self.send_response(404); self._cors(); self.end_headers(); return
        cnames = sorted(_parse_color_imgs(p.get("color_imgs")).keys())
        if n < 0 or n >= len(cnames):
            self.send_response(404); self._cors(); self.end_headers(); return
        imgs = _parse_color_imgs(p.get("color_imgs"))[cnames[n]]
        if m < 0 or m >= len(imgs):
            self.send_response(404); self._cors(); self.end_headers(); return
        self._serve_ref(imgs[m])

    def _serve_ref(self, img):
        """Bitta rasm manbasi: URL bo'lsa redirect, Telegram fayl bo'lsa proxy."""
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
    dblabel = f"mysql://{MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}" if DB_TYPE == "mysql" else DB_PATH
    print(f"API http://0.0.0.0:{HTTP_PORT} — db: {dblabel}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
