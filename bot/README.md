# SAMA BASIC — admin bot

Buyurtmalarni qabul qiladi, bаzaga yozadi va adminlarga inline tugmalar bilan yuboradi.
Faqat Python standart kutubxonasi — `pip install` shart emas.

## Lokal ishga tushirish

```bash
cd bot
python adminbot.py
# API: http://localhost:8003/api/health
```

Atrof-muhit o'zgaruvchilari (ixtiyoriy):
- `BOT_TOKEN` — default kod ichida
- `ADMIN_IDS` — default `7692914031,7148674443`
- `PORT` — default `8003`
- `DB_TYPE` — `sqlite` (default, `orders.db` fayl) yoki `mysql`
- MySQL rejimda: `MYSQL_HOST`, `MYSQL_PORT` (3306), `MYSQL_USER`,
  `MYSQL_PASSWORD`, `MYSQL_DB` (`samabasic`) + `pip install pymysql`

## SQLite → MySQL ko'chirish

```bash
cd bot
pip install pymysql
export DB_TYPE=mysql MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DB=samabasic
python migrate_sqlite_mysql.py   # orders.db dagi hamma narsa MySQL'ga ko'chadi
python adminbot.py               # endi MySQL bilan ishlaydi
```

## Doimiy hosting (Render, bepul)

1. `bot/` papkani GitHub'ga yuklang (yoki Render'da "New → Web Service" → repo).
2. `BOT_TOKEN` ni Environment'da kiriting (secret).
3. Deploy'dan keyin berilgan URL'ni nusxalang, masalan:
   `https://sama-adminbot.onrender.com`
4. `site/common.js` va `landing/app.js` ichidagi `ORDER_API_URL` ga yozing:
   ```js
   const ORDER_API_URL = "https://sama-adminbot.onrender.com";
   ```

## Bot buyruqlari (faqat adminlar)

- `/start` — panel menyusi
- `/orders` — buyurtmalar (Kutulmoqda / Qabul / Rad filtrlari + sahifalash)
- `/stats` — statistika (jami/bugun/holatlar)
- `/addproduct` — yangi mahsulotni bosqichma-bosqich qo'shish (nom, kategoriya, narx, o'lcham, rang, material, tavsif, rasm)
- `/products` — mahsulotlar ro'yxati (o'chirish tugmalari bilan)
- `/delproduct ID` — mahsulotni o'chirish
- `/promo_add KOD FOIZ [SONI]`, `/promo_list` — promokodlar
- `/setcard KARTA` — oldindan to'lov kartasi

## Mahsulot qo'shish (bot orqali)

/addproduct → deyarli hamma qadam inline tugmalar: nom yoziladi, kategoriya/narx/qoldiq/
o'lcham/rang/material tugmadan tanlanadi (yozish varianti ham bor). Oxirida **har bir
rang uchun alohida foto** yuboriladi (1-4 ta, o'tkazish: «-»). Kamida bitta rangga rasm
shart. Saqlangan mahsulot saytda (bosh sahifa, do'kon, mahsulot sahifasi) avtomatik
ko'rinadi, rang tanlanganda o'sha rang rasmlari chiqadi.

API:
- `GET /api/products` — faol mahsulotlar ro'yxati (`colorGalleries` bilan)
- `GET /api/img/<id>` — mahsulot rasmi (Telegram fayl bo'lsa proxy, URL bo'lsa redirect)
- `GET /api/cimg/<id>/<rang>/<rasm>` — rangga tegishli rasm (masalan: `/api/cimg/5/0/1`)

## Buyurtma tugmalari

- ✅ Qabul qilish / ❌ Rad etish (yangi buyurtmada)
- 🟡 Tayyorlanmoqda / 🚚 Yo'lda / 🏁 Yetkazildi / ❌ Bekor
- Tugma bosilganda holat bazaga yoziladi va xabar yangilanadi.
