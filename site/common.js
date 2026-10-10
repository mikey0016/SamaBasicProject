/* =========================================================
   Sama Basic — umumiy (common)
   Ma'lumot, savat, sevimlilar, hisob — barcha sahifa uchun
   ========================================================= */

// ---------- Telegram buyurtma sozlamasi ----------
// @BotFather dan olingan bot TOKEN va admin CHAT ID ni yozing.
// Masalan: const TELEGRAM_BOT_TOKEN = "123456:ABC...";
//          const TELEGRAM_ADMIN_IDS = [123456789];
const TELEGRAM_BOT_TOKEN = "8975220527:AAHXUl4SixHdXAELqOdVWtU8WwZz3M3jASY";
const TELEGRAM_ADMIN_IDS = [7692914031, 7148674443];

// ---------- Mahsulotlar ----------
const PRODUCTS = [
  { id:1, name:"Oversize Basic Futbolka", cat:"kiyimlar", price:189000, old:229000, base:"p1", tag:"Yangi",
    material:"100% paxta, 240 g/m²", sizes:["S","M","L","XL","XXL"], colors:["Oq","Qora","Olive"],
    stock:12, rating:4.8, reviews:34,
    desc:"Kundalik kiyish uchun og'ir paxta futbolka. Erkin oversize bichim, yelka choklari mustahkam. Yuvilgandan keyin shaklini yo'qotmaydi.",
    care:"30°C da yuvish, dazmollash past haroratda." },

  { id:2, name:"Olive Klassik Ko'ylak", cat:"kiyimlar", price:349000, old:null, base:"p2", tag:"Top",
    material:"70% paxta, 30% zig'ir", sizes:["S","M","L","XL"], colors:["Olive","Bej","Ko'k"],
    stock:8, rating:4.9, reviews:21,
    desc:"Zaytun yashil klassik ko'ylak. Tabiiy mato nafas oladi, ofis va kundalik uchun mos. Minimal dizayn, ortiqcha bezaksiz.",
    care:"Quruq tozalash yoki 30°C da nozik yuvish." },

  { id:3, name:"Minimal Chinos Shim", cat:"kiyimlar", price:299000, old:379000, base:"p1", tag:"Chegirma",
    material:"98% paxta, 2% elastan", sizes:["28","30","32","34","36"], colors:["Bej","Olive","Qora"],
    stock:15, rating:4.7, reviews:45,
    desc:"To'g'ri bichimli chinos shim. Bir oz elastan qo'shilgan, harakatlanishga qulay. Ham klassik, ham smart-casual uslubga mos.",
    care:"30°C da yuvish, o'rtacha dazmol." },

  { id:4, name:"To'q Yashil Kardigan", cat:"kiyimlar", price:459000, old:null, base:"p2", tag:null,
    material:"50% jun, 50% akril", sizes:["S","M","L","XL"], colors:["To'q yashil","Kulrang"],
    stock:6, rating:4.6, reviews:18,
    desc:"Yumshoq trikotaj kardigan. Kuzgi va bahorgi ob-havoga ideal. Issiq, lekin og'ir emas.",
    care:"Qo'lda yuvish tavsiya etiladi." },

  { id:5, name:"Teri Aksessuar Sumkasi", cat:"aksessuarlar", price:520000, old:640000, base:"p2", tag:"Chegirma",
    material:"Tabiiy teri", sizes:["One Size"], colors:["Olive","Jigarrang","Qora"],
    stock:5, rating:4.9, reviews:29,
    desc:"Qo'lda ishlangan tabiiy teri sumka. Ichki cho'ntaklar, mustahkam fermuar. Har kuni uchun nafis aksessuar.",
    care:"Nam mato bilan artish, to'g'ridan-to'g'ri quyoshdan saqlash." },

  { id:6, name:"Minimal Kamar", cat:"aksessuarlar", price:159000, old:null, base:"p1", tag:null,
    material:"Tabiiy teri + metall tugma", sizes:["90cm","100cm","110cm"], colors:["Qora","Olive","Jigarrang"],
    stock:20, rating:4.7, reviews:52,
    desc:"Oddiy va mustahkam kamar. Har qanday shim va kiyimga mos keladi. Zanglamaydigan metall furnitura.",
    care:"Quruq joyda saqlash." },

  { id:7, name:"Basic Paxta Sharf", cat:"aksessuarlar", price:129000, old:169000, base:"p2", tag:"Chegirma",
    material:"100% paxta", sizes:["One Size"], colors:["Olive","Krem","Kulrang"],
    stock:18, rating:4.8, reviews:37,
    desc:"Yumshoq paxta sharf. Bo'yinni himoya qiladi, minimal uslubni to'ldiradi. Har faslda kiyish mumkin.",
    care:"30°C da yuvish." },

  { id:8, name:"Zaytun Rang Ko'zoynak", cat:"aksessuarlar", price:239000, old:null, base:"p1", tag:"Yangi",
    material:"Asetat ramka, UV400 linza", sizes:["One Size"], colors:["Zaytun","Qora"],
    stock:10, rating:4.5, reviews:14,
    desc:"Zaytun rang ramkali quyoshdan saqlovchi ko'zoynak. Yengil, UV400 himoya. Zamonaviy minimal dizayn.",
    care:"Maxsus mato bilan artish." },
];

// Galereya view'lari
const VIEW_LABELS = ["Old ko'rinish", "Orqa ko'rinish", "Yaqin detal", "Zoom"];
PRODUCTS.forEach(p => {
  p.gallery = ["front", "back", "detail", "zoom"].map((v, i) => ({
    src: `assets/views/${p.base}_${v}.jpg`,
    label: VIEW_LABELS[i]
  }));
  p.img = p.gallery[0].src;
});

const CATS = { kiyimlar: "Kiyimlar", aksessuarlar: "Aksessuarlar" };
const getProduct = id => PRODUCTS.find(p => p.id === +id);
const fmt = n => n.toLocaleString("ru-RU").replace(/,/g, " ") + " so'm";
const discountPct = p => p.old ? Math.round((1 - p.price / p.old) * 100) : 0;

const $  = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

// ---------- Saqlash yordamchilari ----------
function load(key, def){ try { const v = JSON.parse(localStorage.getItem(key)); return v === null || v === undefined ? def : v; } catch(e){ return def; } }
function save(key, val){ localStorage.setItem(key, JSON.stringify(val)); }

// ---------- Holat ----------
let cart     = load("sama_cart", []);
let wishlist = load("sama_wishlist", []);
let user     = load("sama_user", null);

// ---------- Savat ----------
const saveCart = () => save("sama_cart", cart);

function addToCart(id, qty = 1){
  const item = cart.find(c => c.id === id);
  if(item) item.qty += qty; else cart.push({ id, qty });
  saveCart(); renderCart();
  const p = getProduct(id);
  if(p) toast(`"${p.name}" savatga qo'shildi (${qty} dona)`);
}
function changeQty(id, d){
  const item = cart.find(c => c.id === id);
  if(!item) return;
  item.qty += d;
  if(item.qty <= 0) cart = cart.filter(c => c.id !== id);
  saveCart(); renderCart(); document.dispatchEvent(new CustomEvent("cart:change"));
}
function removeItem(id){
  cart = cart.filter(c => c.id !== id);
  saveCart(); renderCart(); document.dispatchEvent(new CustomEvent("cart:change"));
}
function clearCart(){ cart = []; saveCart(); renderCart(); document.dispatchEvent(new CustomEvent("cart:change")); }
const cartCount = () => cart.reduce((s,c) => s + c.qty, 0);
const cartTotal = () => cart.reduce((s,c) => { const p = getProduct(c.id); return s + (p ? p.price * c.qty : 0); }, 0);

// ---------- Sevimlilar (wishlist) ----------
const saveWish = () => save("sama_wishlist", wishlist);
const isWished = id => wishlist.includes(+id);
function toggleWish(id){
  id = +id;
  if(isWished(id)){ wishlist = wishlist.filter(x => x !== id); toast("Sevimlilardan olib tashlandi"); }
  else { wishlist.push(id); toast("Sevimlilarga qo'shildi ♥"); }
  saveWish(); renderWishCount();
  document.dispatchEvent(new CustomEvent("wishlist:change"));
}
function renderWishCount(){
  const el = $("#wishCount");
  if(el) el.textContent = wishlist.length;
}

// ---------- Hisob (auth) ----------
const USER_ICON = `<svg viewBox="0 0 24 24" width="21" height="21"><path fill="currentColor" d="M12 12a5 5 0 100-10 5 5 0 000 10zm0 2c-4.4 0-8 2.7-8 6v2h16v-2c0-3.3-3.6-6-8-6z"/></svg>`;

function setUser(u){ user = u; save("sama_user", u); renderAccount(); }
function logout(){ user = null; save("sama_user", null); renderAccount(); toast("Hisobdan chiqdingiz"); }

function renderAccount(){
  const el = $("#accountArea");
  if(!el) return;
  if(user){
    el.innerHTML = `
      <div class="acct" id="acctBtn" tabindex="0" role="button" aria-label="Hisobim">
        <span class="acct__ava">${(user.name || "U")[0].toUpperCase()}</span>
        <span class="acct__name">${user.name || user.email}</span>
        <span class="acct__caret">▾</span>
        <div class="acct__menu">
          <a href="wishlist.html">Sevimlilar</a>
          <a href="cart.html">Savat</a>
          <a href="checkout.html">Buyurtmalarim</a>
          <button id="logoutBtn">Chiqish</button>
        </div>
      </div>`;
  } else {
    el.innerHTML = `
      <a class="acct acct--guest" href="login.html" title="Kirish / Ro'yxatdan o'tish">
        ${USER_ICON}<span class="acct__label">Kirish</span>
      </a>`;
  }
}
function requireLogin(redirect){
  if(user) return true;
  toast("Avval hisobingizga kiring");
  setTimeout(() => location.href = `login.html?next=${encodeURIComponent(redirect || location.pathname.split("/").pop())}`, 800);
  return false;
}

// ---------- Telegram'ga buyurtma yuborish ----------
function escHtml(s){ return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function mapsUrl(lat, lon){ return `https://maps.google.com/?q=${(+lat).toFixed(6)},${(+lon).toFixed(6)}`; }

function buildOrderText(o){
  const lines = o.items.map((it, i) => `${i + 1}. ${escHtml(it.name)} — ${it.qty} × ${fmt(it.price)} = ${fmt(it.price * it.qty)}`);
  const locLine = (o.loc && isFinite(o.loc.lat) && isFinite(o.loc.lon))
    ? `🗺 Lokatsiya: <a href="${mapsUrl(o.loc.lat, o.loc.lon)}">${(+o.loc.lat).toFixed(6)}, ${(+o.loc.lon).toFixed(6)}</a>\n`
    : "";
  const promoLine = o.promo ? `🎟 Promo: <b>${escHtml(o.promo)}</b> (-${o.discount_pct || "?"}%)\n` : "";
  const prepayLine = o.prepay
    ? `💳 Oldindan 50%: <b>${fmt(o.prepay)}</b>\n💵 Qolgan (yetkazishda): <b>${fmt((o.total || 0) - o.prepay)}</b>\n`
    : "";
  return (
`🛍 <b>Yangi buyurtma ${escHtml(o.no)}</b>
📦 Manba: ${escHtml(o.source)}

👤 Mijoz: ${escHtml(o.name)}
📞 Telefon: ${escHtml(o.phone)}
📍 Manzil: ${escHtml(o.address)}
${locLine}🚚 Yetkazib berish: ${escHtml(o.ship)}
💳 To'lov: ${escHtml(o.pay)}
📝 Izoh: ${escHtml(o.note || "—")}

🧾 Tarkib:
${lines.join("\n")}

🧮 Mahsulotlar: ${fmt(o.subtotal)}
${o.discount ? `🎟 Chegirma: -${fmt(o.discount)}\n` : ""}🚚 Yetkazish: ${o.shipCost ? fmt(o.shipCost) : "Bepul"}
💰 <b>Jami: ${fmt(o.total)}</b>
${promoLine}${prepayLine}`);
}

async function sendOrderToTelegram(text, loc){
  if(!TELEGRAM_BOT_TOKEN || !TELEGRAM_ADMIN_IDS.length){
    console.warn("Telegram sozlanmagan: TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_IDS bo'sh");
    return { ok:false, skipped:true };
  }
  const api = m => `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${m}`;
  const sendTo = (id, payload) =>
    fetch(api(payload.loc ? "sendLocation" : "sendMessage"), {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(payload.loc
        ? { chat_id:id, latitude:+payload.loc.lat, longitude:+payload.loc.lon }
        : { chat_id:id, text:payload.text, parse_mode:"HTML" })
    }).then(r => r.json())
     .then(j => ({ id, ok:!!(j && j.ok), desc:(j && j.description) || "" }))
     .catch(() => ({ id, ok:false, desc:"tarmoq xatosi" }));
  try{
    const results = await Promise.all(TELEGRAM_ADMIN_IDS.map(id => sendTo(id, { text })));
    // Kamida bitta adminga borsa — buyurtma qabul (qolganiga alohida urinish shart emas)
    if(!results.some(r => r.ok)) return { ok:false, error:results[0]?.desc || "yuborilmadi" };
    // Lokatsiya bo'lsa — adminga xarita pini ham yuboriladi (xatosi buyurtmani buzmaydi)
    if(loc && isFinite(loc.lat) && isFinite(loc.lon)){
      await Promise.all(TELEGRAM_ADMIN_IDS.map(id => sendTo(id, { loc })));
    }
    return { ok:true };
  }catch(err){
    return { ok:false, error:"tarmoq xatosi" };
  }
}

// ---------- Buyurtma xaritasi (Leaflet, kalitsiz) ----------
let orderLat = null, orderLon = null;
function setOrderLoc(lat, lon){ orderLat = +lat; orderLon = +lon; updateMapLabel(); }
function getOrderLoc(){ return (orderLat !== null && orderLon !== null) ? { lat:orderLat, lon:orderLon } : null; }

// Nominatim javobini bizning viloyatlar ro'yxatiga moslash
const REGION_KEYS = [
  ["toshkent", "Toshkent shahri"], ["tashkent", "Toshkent shahri"],
  ["samarqand", "Samarqand"], ["samarkand", "Samarqand"],
  ["buxoro", "Buxoro"], ["bukhara", "Buxoro"],
  ["andijon", "Andijon"], ["andijan", "Andijon"],
  ["farg'ona", "Farg'ona"], ["fargona", "Farg'ona"], ["fergana", "Farg'ona"],
  ["namangan", "Namangan"],
  ["qashqadaryo", "Qashqadaryo"], ["kashkadarya", "Qashqadaryo"],
  ["surxondaryo", "Surxondaryo"], ["surkhandarya", "Surxondaryo"],
  ["xorazm", "Xorazm"], ["khorezm", "Xorazm"],
  ["navoiy", "Navoiy"], ["navoi", "Navoiy"],
  ["jizzax", "Jizzax"], ["jizzakh", "Jizzax"],
  ["sirdaryo", "Sirdaryo"], ["sirdarya", "Sirdaryo"],
  ["qoraqalpog", "Qoraqalpog'iston"], ["karakalpakstan", "Qoraqalpog'iston"],
];
function matchRegion(s){
  s = (s || "").toLowerCase();
  for(const [k, v] of REGION_KEYS){ if(s.includes(k)) return v; }
  return "";
}

// Xaritadan nuqta tanlanganda manzil maydonlarini avtomatik to'ldirish
async function fillAddress(lat, lon){
  try{
    const r = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=jsonv2&accept-language=uz`);
    const j = await r.json();
    const a = (j && j.address) || {};
    const form = document.querySelector("#orderForm");
    if(!form) return;
    const reg = matchRegion(a.state || a.region || "");
    if(reg){
      const sel = form.querySelector('[name="region"]');
      if(sel) sel.value = reg;
    }
    const city = a.city || a.town || a.village || a.county || "";
    const addr = [a.road, a.house_number, a.suburb].filter(Boolean).join(", ");
    if(city){ const el = form.querySelector('[name="city"]'); if(el) el.value = city; }
    if(addr){ const el = form.querySelector('[name="address"]'); if(el) el.value = addr; }
    if(city || addr) toast("Manzil avtomatik to'ldirildi ✓");
  }catch(e){}
}

function updateMapLabel(){
  const el = document.querySelector("#mapCoords");
  if(!el) return;
  const loc = getOrderLoc();
  el.innerHTML = loc
    ? `📍 Tanlandi: <a href="${mapsUrl(loc.lat, loc.lon)}" target="_blank" rel="noopener">${loc.lat.toFixed(6)}, ${loc.lon.toFixed(6)}</a>`
    : "Xaritani bosing yoki «Meni topish»ni bosing";
}

function initOrderMap(){
  const box = document.querySelector("#orderMap");
  if(!box) return;
  orderLat = null; orderLon = null; updateMapLabel();
  if(!window.L){
    box.innerHTML = `<p class="mapfallback">Xarita yuklanmadi — manzilni qo'lda yozing.</p>`;
    return;
  }
  const TASHKENT = [41.3111, 69.2797];
  const map = L.map("orderMap").setView(TASHKENT, 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom:19, attribution:"© OpenStreetMap" }).addTo(map);
  let marker = null;
  const place = (lat, lon) => {
    setOrderLoc(lat, lon);
    fillAddress(lat, lon);
    if(marker) marker.setLatLng([lat, lon]);
    else{
      marker = L.marker([lat, lon], { draggable:true }).addTo(map);
      marker.on("dragend", () => { const p = marker.getLatLng(); setOrderLoc(p.lat, p.lng); fillAddress(p.lat, p.lng); });
    }
  };
  map.on("click", e => place(e.latlng.lat, e.latlng.lng));
  document.querySelector("#findMe")?.addEventListener("click", () => {
    if(!navigator.geolocation){ toast("Brauzer joylashuvni qo'llamaydi"); return; }
    toast("Joylashuv aniqlanmoqda...");
    navigator.geolocation.getCurrentPosition(
      pos => { const la = pos.coords.latitude, lo = pos.coords.longitude; map.setView([la, lo], 15); place(la, lo); },
      () => toast("Joylashuvni aniqlab bo'lmadi"),
      { timeout:10000 }
    );
  });
  setTimeout(() => map.invalidateSize(), 150);
}

// ---------- Buyurtma yuborish (server orqali, bo'lmasa to'g'ridan-to'g'ri) ----------
// Backend (bot/adminbot.py) manzili, masalan: "https://sama-bot.onrender.com"
// Bo'sh bo'lsa buyurtma to'g'ridan-to'g'ri Telegram'ga ketadi (hozirgi rejim).
const ORDER_API_URL = "https://rid-brass-llc-miscellaneous.trycloudflare.com";

// ---------- Bot orqali qo'shilgan mahsulotlarni serverdan yuklash ----------
function loadServerProducts(){
  if(!ORDER_API_URL) return Promise.resolve();
  const base = ORDER_API_URL.replace(/\/$/, "");
  return fetch(base + "/api/products")
    .then(r => r.json())
    .then(j => {
      if(!j || !j.ok || !Array.isArray(j.products)) return;
      let added = false;
      j.products.forEach(sp => {
        if(sp == null || sp.id == null || PRODUCTS.some(p => p.id === sp.id)) return;
        sp.sizes  = (Array.isArray(sp.sizes)  && sp.sizes.length)  ? sp.sizes  : ["One Size"];
        sp.colors = (Array.isArray(sp.colors) && sp.colors.length) ? sp.colors : ["Standart"];
        const srcs = (Array.isArray(sp.images) && sp.images.length) ? sp.images : (sp.img ? [sp.img] : []);
        sp.gallery = srcs.map((s, i) => ({ src: /^https?:/.test(s) ? s : base + s, label: `Ko'rinish ${i + 1}` }));
        sp.img = sp.gallery.length ? sp.gallery[0].src : "assets/logo.jpg";
        sp.rating = sp.rating || 5;
        sp.reviews = sp.reviews || 0;
        sp.base = sp.base || "p1";
        sp.material = sp.material || "—";
        sp.desc = sp.desc || "Tavsif kiritilmagan";
        sp.care = sp.care || "Ko'rsatma yo'q";
        PRODUCTS.push(sp);
        added = true;
      });
      if(added) document.dispatchEvent(new CustomEvent("products:update"));
    })
    .catch(() => {});
}

async function submitOrder(order){
  if(ORDER_API_URL){
    try{
      const r = await fetch(ORDER_API_URL.replace(/\/$/, "") + "/api/order", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(order)
      });
      const j = await r.json();
      if(j && j.ok) return { ok:true, via:"server", id:j.id };
      console.warn("Order API:", j);
    }catch(err){ console.warn("Order API:", err); }
  }
  return sendOrderToTelegram(buildOrderText(order), order.loc);
}

// ---------- Toast ----------
let toastTimer;
function toast(msg){
  const el = $("#toast");
  if(!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
}

// ---------- Savat drawer ----------
function openCart(){ $("#cartDrawer")?.classList.add("open"); $("#overlay")?.classList.add("open"); }
function closeCart(){ $("#cartDrawer")?.classList.remove("open"); $("#overlay")?.classList.remove("open"); }

function renderCart(){
  const cc = $("#cartCount"); if(cc) cc.textContent = cartCount();
  const tot = $("#cartTotal"); if(tot) tot.textContent = fmt(cartTotal());

  const body = $("#cartItems");
  if(!body) return;
  if(!cart.length){
    body.innerHTML = `<p class="drawer__empty">Savat hozircha bo'sh 🛍️<br>Mahsulot qo'shing!</p>`;
    return;
  }
  body.innerHTML = cart.map(c => {
    const p = getProduct(c.id);
    if(!p) return "";
    return `
      <div class="citem">
        <a href="product.html?id=${p.id}"><img src="${p.img}" alt="${p.name}"></a>
        <div class="citem__info">
          <h4><a href="product.html?id=${p.id}">${p.name}</a></h4>
          <span>${fmt(p.price * c.qty)}</span>
          <div class="citem__qty">
            <button data-dec="${p.id}">−</button>
            <span>${c.qty}</span>
            <button data-inc="${p.id}">+</button>
          </div>
        </div>
        <button class="citem__remove" data-remove="${p.id}" aria-label="O'chirish">🗑</button>
      </div>`;
  }).join("");
}

// ---------- Mahsulot kartasi ----------
// Kartadagi miqdor tanlagichi progressiv: default'da faqat "+" ko'rinadi,
// bosilgach "− N +" ochiladi. Tanlov setka qayta chizilganda ham saqlanadi.
const cardQty = {};
function getCardQty(id){ return cardQty[id] || 1; }
function isQtyOpen(id){ return id in cardQty; }
function setCardQty(id, v){ cardQty[id] = Math.max(1, v || 1); }
function closeQty(id){ delete cardQty[id]; }
function qtyInner(id){
  return isQtyOpen(id)
    ? `<button class="qty__btn" data-qdec="${id}" aria-label="Kamaytirish">−</button><span class="qty__val" data-qval="${id}">${getCardQty(id)}</span><button class="qty__btn" data-qinc="${id}" aria-label="Ko'paytirish">+</button>`
    : `<button class="qty__btn qty__solo" data-qinc="${id}" aria-label="Miqdor tanlash">+</button>`;
}

function productCardHTML(p, i = 0){
  const wished = isWished(p.id);
  return `
    <article class="card" style="animation-delay:${i*40}ms" data-card="${p.id}">
      <div class="card__media">
        <a href="product.html?id=${p.id}" aria-label="${p.name}">
          <img src="${p.img}" alt="${p.name}" loading="lazy">
        </a>
        ${p.tag ? `<span class="card__tag ${p.tag==='Chegirma'?'card__tag--sale':''}">${p.tag}</span>` : ""}
        <button class="card__fav ${wished?'active':''}" data-fav="${p.id}" aria-label="Sevimlilar">${wished?'♥':'♡'}</button>
      </div>
      <div class="card__body">
        <p class="card__cat">${CATS[p.cat] || p.cat}</p>
        <h3 class="card__name"><a href="product.html?id=${p.id}">${p.name}</a></h3>
        <div class="card__price">
          <b>${fmt(p.price)}</b>
          ${p.old ? `<s>${fmt(p.old)}</s>` : ""}
        </div>
        <div class="card__foot">
          <div class="qty" data-qty="${p.id}">
            ${qtyInner(p.id)}
          </div>
          <button class="card__add" data-add="${p.id}">Savatga</button>
        </div>
      </div>
    </article>`;
}

function bindCardEvents(root){
  if(!root || root.__cardBound) return;
  root.__cardBound = true;
  root.addEventListener("click", e => {
    const qinc = e.target.closest("[data-qinc]");
    const qdec = e.target.closest("[data-qdec]");
    const add  = e.target.closest("[data-add]");
    const fav  = e.target.closest("[data-fav]");

    if(fav){
      toggleWish(fav.dataset.fav);
      const on = isWished(fav.dataset.fav);
      fav.classList.toggle("active", on);
      fav.textContent = on ? "♥" : "♡";
      return;
    }
    if(qinc || qdec){
      const id = qinc ? qinc.dataset.qinc : qdec.dataset.qdec;
      const box = root.querySelector(`[data-qty="${id}"]`);
      if(!box) return;
      const valEl = box.querySelector(`[data-qval="${id}"]`);
      if(qinc){
        if(valEl){ const n = +valEl.textContent + 1; setCardQty(id, n); }
        else setCardQty(id, 1); // birinchi bosish — stepperni 1 bilan ochish
      }else{
        if(!valEl) return;
        const cur = +valEl.textContent;
        if(cur <= 1) closeQty(id); // 1 da "−" — yana faqat "+" ga yig'ish
        else setCardQty(id, cur - 1);
      }
      box.innerHTML = qtyInner(id);
      return;
    }
    if(add){
      const id = +add.dataset.add;
      const box = root.querySelector(`[data-qty="${id}"]`);
      const valEl = box ? box.querySelector(`[data-qval="${id}"]`) : null;
      if(!valEl && !isQtyOpen(id)){
        toast("Avval «+» ni bosib sotib olmoqchi bo'lgan narsangizni tanlang");
        return;
      }
      const qty = valEl ? +valEl.textContent : getCardQty(id);
      addToCart(id, qty);
      closeQty(id);
      if(box) box.innerHTML = qtyInner(id);
    }
  });
}

// ---------- Umumiy UI ----------
function initCommonUI(){
  loadServerProducts();
  renderCart();
  renderWishCount();
  renderAccount();

  $("#cartBtn")?.addEventListener("click", openCart);
  $("#closeCart")?.addEventListener("click", closeCart);
  $("#overlay")?.addEventListener("click", closeCart);

  $("#cartItems")?.addEventListener("click", e => {
    const inc = e.target.closest("[data-inc]");
    const dec = e.target.closest("[data-dec]");
    const rm  = e.target.closest("[data-remove]");
    if(inc) changeQty(+inc.dataset.inc, 1);
    if(dec) changeQty(+dec.dataset.dec, -1);
    if(rm)  removeItem(+rm.dataset.remove);
  });

  $("#checkout")?.addEventListener("click", () => {
    if(!cart.length){ toast("Savat bo'sh"); return; }
    location.href = "checkout.html";
  });

  // Hisob menyusi (bir marta bog'lanadi)
  document.addEventListener("click", e => {
    if(e.target.closest("#logoutBtn")){ logout(); return; }
    const acct = $("#acctBtn");
    if(acct && e.target.closest("#acctBtn") && !e.target.closest(".acct__menu")){
      acct.classList.toggle("open");
      return;
    }
    acct?.classList.remove("open");
  });

  // Burger
  const nav = $("#nav"), burger = $("#burger");
  if(burger && nav){
    burger.addEventListener("click", () => { nav.classList.toggle("open"); burger.classList.toggle("open"); });
    nav.querySelectorAll("a").forEach(a => a.addEventListener("click", () => { nav.classList.remove("open"); burger.classList.remove("open"); }));
  }

  window.addEventListener("scroll", () => $("#header")?.classList.toggle("scrolled", window.scrollY > 10));

  document.addEventListener("keydown", e => {
    if(e.key === "Escape"){ closeCart(); $("#searchBar")?.classList.remove("open"); nav?.classList.remove("open"); burger?.classList.remove("open"); }
  });
}
