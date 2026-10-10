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
- `/orders` — so'nggi 10 buyurtma
- `/stats` — statistika (jami/bugun/holatlar)
- `/addproduct` — yangi mahsulotni bosqichma-bosqich qo'shish (nom, kategoriya, narx, o'lcham, rang, material, tavsif, rasm)
- `/products` — mahsulotlar ro'yxati (o'chirish tugmalari bilan)
- `/delproduct ID` — mahsulotni o'chirish
- `/promo_add KOD FOIZ [SONI]`, `/promo_list` — promokodlar
- `/setcard KARTA` — oldindan to'lov kartasi

## Mahsulot qo'shish (bot orqali)

`/addproduct` → bot navbat bilan savol beradi. Rasm bosqichida **foto** yuboring yoki
«-» bilan o'tkazib yuboring. Saqlangan mahsulot saytda (bosh sahifa, do'kon, mahsulot
sahifasi) avtomatik ko'rinadi.

API:
- `GET /api/products` — faol mahsulotlar ro'yxati
- `GET /api/img/<id>` — mahsulot rasmi (Telegram fayl bo'lsa proxy, URL bo'lsa redirect)

## Buyurtma tugmalari

- ✅ Qabul qilish / ❌ Rad etish (yangi buyurtmada)
- 🟡 Tayyorlanmoqda / 🚚 Yo'lda / 🏁 Yetkazildi / ❌ Bekor
- Tugma bosilganda holat bazaga yoziladi va xabar yangilanadi.
