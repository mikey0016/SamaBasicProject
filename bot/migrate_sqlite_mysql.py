#!/usr/bin/env python3
"""SQLite (orders.db) dagi barcha jadvallarni MySQL'ga ko'chirish.

Ishlatish (bot/ papkada):
    pip install pymysql
    export DB_TYPE=mysql MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DB=samabasic
    python migrate_sqlite_mysql.py

ID lar saqlanib qoladi (buyurtma/havolalar buzilmaydi).
Qayta ishga tushirish xavfsiz: mavjud ID lar yangilanadi (REPLACE).
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["DB_TYPE"] = "mysql"
import adminbot  # noqa: E402


def main():
    adminbot.init_db()
    src = sqlite3.connect(adminbot.DB_PATH)
    src.row_factory = sqlite3.Row
    dst = adminbot.db()
    tables = ["orders", "promos", "kv", "products"]
    for tbl in tables:
        try:
            rows = [dict(r) for r in src.execute(f"SELECT * FROM {tbl}").fetchall()]
        except sqlite3.OperationalError as e:
            print(f"{tbl}: o'tkazib yuborildi ({e})", flush=True)
            continue
        if not rows:
            print(f"{tbl}: bo'sh", flush=True)
            continue
        cols = list(rows[0].keys())
        for r in rows:
            ph = ",".join(["?"] * len(cols))
            if adminbot.DB_TYPE == "mysql":
                upd = ",".join(f"{c}=VALUES({c})" for c in cols if c != "id")
                q = (f"INSERT INTO {tbl}({','.join(cols)}) VALUES({ph})"
                     + (f" ON DUPLICATE KEY UPDATE {upd}" if upd else ""))
            else:
                q = f"INSERT OR REPLACE INTO {tbl}({','.join(cols)}) VALUES({ph})"
            dst.execute(q, tuple(r[c] for c in cols))
        dst.commit()
        print(f"{tbl}: {len(rows)} ta ko'chirildi", flush=True)
    dst.close()
    src.close()
    print("Tayyor ✅", flush=True)


if __name__ == "__main__":
    main()
