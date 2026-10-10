/* =========================================================
   SAMA BASIC — landing (bir sahifa)
   ========================================================= */

// ---------- Telegram buyurtma sozlamasi ----------
// @BotFather dan olingan bot TOKEN va admin CHAT ID ni yozing.
// Masalan: const TELEGRAM_BOT_TOKEN = "123456:ABC...";
//          const TELEGRAM_ADMIN_IDS = [123456789];
const TELEGRAM_BOT_TOKEN = "8975220527:AAHXUl4SixHdXAELqOdVWtU8WwZz3M3jASY";
const TELEGRAM_ADMIN_IDS = [7692914031, 7148674443];

// ---------- Mahsulotlar ----------
const VIEWS = [
  { key: "front",  label: "Old ko'rinish" },
  { key: "back",   label: "Orqa ko'rinish" },
  { key: "detail", label: "Yaqin detal" },
  { key: "zoom",   label: "Zoom" },
];

const PRODUCTS = [
  { id:1, name:"Oversize Basic Futbolka", cat:"kiyimlar", price:189000, old:229000, base:"p1", tag:"Yangi",
    material:"100% paxta, 240 g/m²", sizes:["S","M","L","XL","XXL"], colors:["Oq","Qora","Olive"], rating:4.8, reviews:34,
    desc:"Kundalik kiyish uchun og'ir paxta futbolka. Erkin oversize bichim, yelka choklari mustahkam." },
  { id:2, name:"Olive Klassik Ko'ylak", cat:"kiyimlar", price:349000, old:null, base:"p2", tag:"Top",
    material:"70% paxta, 30% zig'ir", sizes:["S","M","L","XL"], colors:["Olive","Bej","Ko'k"], rating:4.9, reviews:21,
    desc:"Zaytun yashil klassik ko'ylak. Tabiiy mato nafas oladi, ofis va kundalik uchun mos." },
  { id:3, name:"Minimal Chinos Shim", cat:"kiyimlar", price:299000, old:379000, base:"p1", tag:"Chegirma",
    material:"98% paxta, 2% elastan", sizes:["28","30","32","34","36"], colors:["Bej","Olive","Qora"], rating:4.7, reviews:45,
    desc:"To'g'ri bichimli chinos shim. Elastan qo'shilgan, harakatlanishga qulay." },
  { id:4, name:"To'q Yashil Kardigan", cat:"kiyimlar", price:459000, old:null, base:"p2", tag:null,
    material:"50% jun, 50% akril", sizes:["S","M","L","XL"], colors:["To'q yashil","Kulrang"], rating:4.6, reviews:18,
    desc:"Yumshoq trikotaj kardigan. Kuzgi va bahorgi ob-havoga ideal." },
  { id:5, name:"Teri Aksessuar Sumkasi", cat:"aksessuarlar", price:520000, old:640000, base:"p2", tag:"Chegirma",
    material:"Tabiiy teri", sizes:["One Size"], colors:["Olive","Jigarrang","Qora"], rating:4.9, reviews:29,
    desc:"Qo'lda ishlangan tabiiy teri sumka. Ichki cho'ntaklar, mustahkam fermuar." },
  { id:6, name:"Minimal Kamar", cat:"aksessuarlar", price:159000, old:null, base:"p1", tag:null,
    material:"Tabiiy teri + metall", sizes:["90cm","100cm","110cm"], colors:["Qora","Olive","Jigarrang"], rating:4.7, reviews:52,
    desc:"Oddiy va mustahkam kamar. Har qanday shim va kiyimga mos keladi." },
  { id:7, name:"Basic Paxta Sharf", cat:"aksessuarlar", price:129000, old:169000, base:"p2", tag:"Chegirma",
    material:"100% paxta", sizes:["One Size"], colors:["Olive","Krem","Kulrang"], rating:4.8, reviews:37,
    desc:"Yumshoq paxta sharf. Bo'yinni himoya qiladi, minimal uslubni to'ldiradi." },
  { id:8, name:"Zaytun Rang Ko'zoynak", cat:"aksessuarlar", price:239000, old:null, base:"p1", tag:"Yangi",
    material:"Asetat ramka, UV400", sizes:["One Size"], colors:["Zaytun","Qora"], rating:4.5, reviews:14,
    desc:"Zaytun rang ramkali quyoshdan saqlovchi ko'zoynak. Yengil, UV400 himoya." },
];

PRODUCTS.forEach(p => {
  p.gallery = VIEWS.map(v => ({ src: `assets/views/${p.base}_${v.key}.jpg`, label: v.label }));
  p.img = p.gallery[0].src;
});

const CATS = { kiyimlar: "Kiyimlar", aksessuarlar: "Aksessuarlar" };
const $  = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const getP = id => PRODUCTS.find(p => p.id === +id);
const fmt = n => n.toLocaleString("ru-RU").replace(/,/g, " ") + " so'm";
const pct = p => p.old ? Math.round((1 - p.price / p.old) * 100) : 0;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));

// ---------- Holat ----------
let cart = [];
try { cart = JSON.parse(localStorage.getItem("sb_landing_cart") || "[]"); } catch(e){ cart = []; }
let activeCat = "all";
// Kartadagi miqdor tanlagichi progressiv: default'da faqat "+" ko'rinadi,
// bosilgach "− N +" ochiladi. Tab almashtirilganda ham saqlanadi.
const cardQty = {};
const getCardQty = id => cardQty[id] || 1;
const isQtyOpen = id => id in cardQty;
const setCardQty = (id, v) => { cardQty[id] = Math.max(1, v || 1); };
const closeQty = id => { delete cardQty[id]; };
const qtyInner = id => isQtyOpen(id)
  ? `<button data-dec="${id}">−</button><span data-val="${id}">${getCardQty(id)}</span><button data-inc="${id}">+</button>`
  : `<button class="qty__solo" data-inc="${id}" aria-label="Miqdor tanlash">+</button>`;
let modalP = null, modalView = 0, modalSize = null, modalQty = 1;

const saveCart = () => localStorage.setItem("sb_landing_cart", JSON.stringify(cart));
const cartCount = () => cart.reduce((s,c) => s + c.qty, 0);
const cartTotal = () => cart.reduce((s,c) => { const p = getP(c.id); return s + (p ? p.price * c.qty : 0); }, 0);

// ---------- Telegram'ga buyurtma yuborish ----------
function mapsUrl(lat, lon){ return `https://maps.google.com/?q=${(+lat).toFixed(6)},${(+lon).toFixed(6)}`; }

function buildOrderText(o){
  const e = s => String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const lines = o.items.map((it, i) => `${i + 1}. ${e(it.name)} — ${it.qty} × ${fmt(it.price)} = ${fmt(it.price * it.qty)}`);
  const locLine = (o.loc && isFinite(o.loc.lat) && isFinite(o.loc.lon))
    ? `🗺 Lokatsiya: <a href="${mapsUrl(o.loc.lat, o.loc.lon)}">${(+o.loc.lat).toFixed(6)}, ${(+o.loc.lon).toFixed(6)}</a>\n`
    : "";
  return (
`🛍 <b>Yangi buyurtma ${e(o.no)}</b>
📦 Manba: ${e(o.source)}

👤 Mijoz: ${e(o.name)}
📞 Telefon: ${e(o.phone)}
📍 Manzil: ${e(o.address)}
${locLine}🚚 Yetkazib berish: ${e(o.ship)}
💳 To'lov: ${e(o.pay)}
📝 Izoh: ${e(o.note || "—")}

🧾 Tarkib:
${lines.join("\n")}

🧮 Mahsulotlar: ${fmt(o.subtotal)}
🚚 Yetkazish: ${o.shipCost ? fmt(o.shipCost) : "Bepul"}
💰 <b>Jami: ${fmt(o.total)}</b>`);
}

async function sendOrderToTelegram(text, loc){
  if(!TELEGRAM_BOT_TOKEN || !TELEGRAM_ADMIN_IDS.length){
    console.warn("Telegram sozlanmagan: BOT_TOKEN / ADMIN_IDS bo'sh");
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
  const el = $("#mapCoords");
  if(!el) return;
  const loc = getOrderLoc();
  el.innerHTML = loc
    ? `📍 Tanlandi: <a href="${mapsUrl(loc.lat, loc.lon)}" target="_blank" rel="noopener">${loc.lat.toFixed(6)}, ${loc.lon.toFixed(6)}</a>`
    : "Xaritani bosing yoki «Meni topish»ni bosing";
}

function initOrderMap(){
  const box = $("#orderMap");
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
  $("#findMe")?.addEventListener("click", () => {
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
const IMG_FALLBACK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23202418'/%3E%3Ctext x='50%25' y='50%25' font-size='26' fill='%23a9b18f' text-anchor='middle'%3ESama Basic%3C/text%3E%3C/svg%3E";

// Bot orqali qo'shilgan mahsulotlarni serverdan yuklash
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
        sp.img = sp.gallery.length ? sp.gallery[0].src : IMG_FALLBACK;
        sp.rating = sp.rating || 5;
        sp.reviews = sp.reviews || 0;
        sp.base = sp.base || "p1";
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
let tTimer;
function toast(msg){
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("on");
  clearTimeout(tTimer);
  tTimer = setTimeout(() => el.classList.remove("on"), 2200);
}

// ---------- Grid ----------
function cardHTML(p, i){
  return `
    <article class="pcard reveal" style="transition-delay:${Math.min(i*55,400)}ms">
      <div class="pcard__media">
        <img src="${p.img}" alt="${esc(p.name)}" loading="lazy">
        ${p.tag ? `<span class="pcard__tag ${p.tag === "Chegirma" ? "sale" : ""}">${p.tag}</span>` : ""}
        <div class="pcard__quick"><button data-open="${p.id}">Batafsil</button></div>
      </div>
      <div class="pcard__body">
        <p class="pcard__cat">${CATS[p.cat]}</p>
        <h3 class="pcard__name">${esc(p.name)}</h3>
        <div class="pcard__price">
          <b>${fmt(p.price)}</b>${p.old ? `<s>${fmt(p.old)}</s>` : ""}
        </div>
        <div class="pcard__row">
          <div class="qty" data-q="${p.id}">
            ${qtyInner(p.id)}
          </div>
          <button class="pcard__add" data-add="${p.id}">Savatga</button>
        </div>
      </div>
    </article>`;
}

function renderGrid(){
  const list = PRODUCTS.filter(p => activeCat === "all" || p.cat === activeCat);
  const grid = $("#grid");
  grid.innerHTML = list.length
    ? list.map(cardHTML).join("")
    : `<p class="grid__empty">Bu kategoriyada mahsulot yo'q.</p>`;
  observeReveals();
}

// ---------- Modal (mahsulot tafsiloti) ----------
function openModal(id){
  modalP = getP(id);
  if(!modalP) return;
  modalView = 0;
  modalSize = modalP.sizes.length === 1 ? modalP.sizes[0] : null;
  modalQty = 1;

  const p = modalP;
  const disc = pct(p);
  $("#modalBody").innerHTML = `
    <div class="pm">
      <div class="pm__gal">
        <div class="pm__main">
          <img id="pmMain" src="${p.gallery[0].src}" alt="${esc(p.name)}">
          ${disc ? `<span class="pm__badge">-${disc}%</span>` : ""}
        </div>
        <div class="pm__thumbs" id="pmThumbs">
          ${p.gallery.map((g,i) => `
            <button class="pm__thumb ${i===0?"on":""}" data-view="${i}">
              <img src="${g.src}" alt="${esc(g.label)}">
            </button>`).join("")}
        </div>
      </div>
      <div class="pm__info">
        <p class="pm__cat">${CATS[p.cat]}</p>
        <h2>${esc(p.name)}</h2>
        <p class="pm__rate"><b>★ ${p.rating}</b> · ${p.reviews} sharh</p>

        <div class="pm__price">
          <b>${fmt(p.price)}</b>
          ${p.old ? `<s>${fmt(p.old)}</s><span class="pm__save">Tejaysiz ${fmt(p.old - p.price)}</span>` : ""}
        </div>

        <p class="pm__desc">${esc(p.desc)}</p>

        <div class="pm__opt">
          <h4>O'lcham</h4>
          <div class="pm__chips" id="pmSizes">
            ${p.sizes.map(s => `<button class="chip ${modalSize===s?"on":""}" data-size="${s}">${s}</button>`).join("")}
          </div>
        </div>

        <div class="pm__opt">
          <h4>Rang</h4>
          <div class="pm__chips" id="pmColors">
            ${p.colors.map((c,i) => `<button class="chip ${i===0?"on":""}" data-color="${c}">${c}</button>`).join("")}
          </div>
        </div>

        <div class="pm__buy">
          <div class="qty" id="pmQty">
            <button id="pmDec">−</button><span id="pmVal">1</span><button id="pmInc">+</button>
          </div>
        </div>

        <button class="btn btn--fill btn--full" id="pmAdd">Savatga qo'shish</button>

        <div class="pm__meta">
          <div><span>Material</span><b>${esc(p.material)}</b></div>
          <div><span>Yetkazish</span><b>5 kun ichida</b></div>
          <div><span>Qaytarish</span><b>Faqat xato/brakda</b></div>
        </div>
      </div>
    </div>`;

  bindModal();
  $("#modal").classList.add("on");
  $("#modal").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeModal(){
  $("#modal").classList.remove("on");
  $("#modal").setAttribute("aria-hidden", "true");
  if(!$("#cart").classList.contains("on")) document.body.style.overflow = "";
}

function bindModal(){
  $("#pmThumbs")?.addEventListener("click", e => {
    const t = e.target.closest("[data-view]");
    if(!t) return;
    modalView = +t.dataset.view;
    $("#pmMain").src = modalP.gallery[modalView].src;
    $$("#pmThumbs .pm__thumb").forEach((el,i) => el.classList.toggle("on", i === modalView));
  });

  $("#pmSizes")?.addEventListener("click", e => {
    const c = e.target.closest("[data-size]");
    if(!c) return;
    $$("#pmSizes .chip").forEach(el => el.classList.remove("on"));
    c.classList.add("on");
    modalSize = c.dataset.size;
  });

  $("#pmColors")?.addEventListener("click", e => {
    const c = e.target.closest("[data-color]");
    if(!c) return;
    $$("#pmColors .chip").forEach(el => el.classList.remove("on"));
    c.classList.add("on");
  });

  $("#pmDec")?.addEventListener("click", () => { modalQty = Math.max(1, modalQty - 1); $("#pmVal").textContent = modalQty; });
  $("#pmInc")?.addEventListener("click", () => { modalQty++; $("#pmVal").textContent = modalQty; });

  $("#pmAdd")?.addEventListener("click", () => {
    if(modalP.sizes.length > 1 && !modalSize){ toast("Iltimos, o'lchamni tanlang"); return; }
    addToCart(modalP.id, modalQty);
    closeModal();
    openCart();
  });
}

// ---------- Savat ----------
function addToCart(id, qty = 1){
  const it = cart.find(c => c.id === +id);
  if(it) it.qty += qty; else cart.push({ id:+id, qty });
  saveCart(); renderCart();
  const p = getP(id);
  if(p) toast(`"${p.name}" savatga qo'shildi (${qty})`);
}

function changeQty(id, d){
  const it = cart.find(c => c.id === +id);
  if(!it) return;
  it.qty += d;
  if(it.qty <= 0) cart = cart.filter(c => c.id !== +id);
  saveCart(); renderCart();
}

function renderCart(){
  const b = $("#cartBadge");
  if(b) b.textContent = cartCount();
  const sum = $("#cartSum");
  if(sum) sum.textContent = fmt(cartTotal());

  const body = $("#cartBody");
  if(!body) return;
  if(!cart.length){
    body.innerHTML = `<p class="cart__empty">Savat bo'sh 🛍️<br>Mahsulot tanlang.</p>`;
    return;
  }
  body.innerHTML = cart.map(c => {
    const p = getP(c.id);
    if(!p) return "";
    return `
      <div class="cline">
        <img src="${p.img}" alt="${esc(p.name)}">
        <div class="cline__i">
          <h4>${esc(p.name)}</h4>
          <b>${fmt(p.price * c.qty)}</b>
          <div class="cline__q">
            <button data-cdec="${p.id}">−</button><span>${c.qty}</span><button data-cinc="${p.id}">+</button>
          </div>
        </div>
        <button class="cline__x" data-crm="${p.id}" aria-label="O'chirish">✕</button>
      </div>`;
  }).join("");
}

const ORDER_REGIONS = ["Toshkent shahri","Toshkent viloyati","Samarqand","Buxoro","Andijon","Farg'ona","Namangan","Qashqadaryo","Surxondaryo","Xorazm","Navoiy","Jizzax","Sirdaryo","Qoraqalpog'iston"];
const ORDER_SHIP_ONE = 40000; // 1 dona olsa — pulli, 2+ dona — bepul

// Qoida: 2+ dona → bepul, 1 dona → 40 000
function orderShipCost(){
  return cartCount() >= 2 ? 0 : ORDER_SHIP_ONE;
}

let promoState = { code:"", pct:0 };
let payCard = "";

function calcTotals(ship){
  const subtotal = cartTotal();
  const discount = promoState.pct ? Math.round(subtotal * promoState.pct / 100) : 0;
  const total = subtotal - discount + ship;
  return { subtotal, discount, total, prepay: Math.round(total / 2) };
}

async function loadPayCard(){
  if(!ORDER_API_URL) return;
  try{
    const r = await fetch(ORDER_API_URL.replace(/\/$/, "") + "/api/config");
    const j = await r.json();
    if(j && j.ok && j.card && $("#prepayCardLine")){ payCard = j.card; renderPrepayCard(); }
  }catch(e){}
}

function renderPrepayCard(){
  const el = $("#prepayCardLine");
  if(!el) return;
  el.innerHTML = payCard
    ? `💳 Oldindan to'lov kartasi (Click/Payme): <b>${payCard}</b>`
    : `💳 50% oldindan to'lov: operatorimiz sizga karta yuboradi.`;
}

function openOrderModal(){
  if(!cart.length){ toast("Savat bo'sh"); return; }
  closeCart();
  renderOrderForm();
  $("#orderModal").classList.add("on");
  $("#orderModal").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  initOrderMap();
}
function closeOrderModal(){
  $("#orderModal").classList.remove("on");
  $("#orderModal").setAttribute("aria-hidden", "true");
  if(!$("#modal").classList.contains("on") && !$("#cart").classList.contains("on")) document.body.style.overflow = "";
}

function osumHTML(){
  const ship = orderShipCost();
  const t = calcTotals(ship);
  const rows = cart.map(c => {
    const p = getP(c.id);
    return `<div class="osum__row"><span>${esc(p.name)} × ${c.qty}</span><b>${fmt(p.price * c.qty)}</b></div>`;
  }).join("");
  return { ship, t, html:
    `${rows}
    ${t.discount ? `<div class="osum__row osum__disc"><span>Promo ${esc(promoState.code)} (-${promoState.pct}%)</span><b>−${fmt(t.discount)}</b></div>` : ""}
    <div class="osum__row"><span>Yetkazish</span><b>${ship ? fmt(ship) : "Bepul"}</b></div>
    <div class="osum__row osum__total"><span>Jami</span><b>${fmt(t.total)}</b></div>
    <div class="osum__prep"><span>Oldindan to'lov · 50%</span><b>${fmt(t.prepay)}</b></div>
    <div class="osum__row"><span>Qolgan (yetkazishda)</span><b>${fmt(t.total - t.prepay)}</b></div>` };
}

function refreshOrderTotals(){
  const s = osumHTML();
  const box = document.querySelector("#orderBody .osum");
  if(box) box.innerHTML = s.html;
  const btn = $("#orderSubmit");
  if(btn) btn.textContent = `Tasdiqlash · ${fmt(s.t.total)} (oldindan ${fmt(s.t.prepay)})`;
}

function renderOrderForm(){
  const s = osumHTML();
  $("#orderBody").innerHTML = `
    <h2 class="ord__title">Buyurtma berish</h2>
    <div class="osum">${s.html}</div>
    <div class="promo promo--dark">
      <input id="promoInput" placeholder="Promokod (% li)" autocomplete="off">
      <button type="button" class="btn btn--line btn--sm" id="promoBtn">Qo'llash</button>
    </div>
    <p class="promo__msg" id="promoMsg">${promoState.pct ? `✅ ${promoState.pct}% qo'llangan` : ""}</p>
    <p class="prepay__note" id="prepayCardLine"></p>
    <form id="orderForm" novalidate>
      <div class="orow">
        <label class="ofield"><span>Ism Familiya *</span><input name="name" required placeholder="Ali Valiyev"></label>
        <label class="ofield"><span>Telefon *</span><input name="phone" required inputmode="tel" placeholder="+998 90 000 00 00"></label>
      </div>
      <div class="orow">
        <label class="ofield"><span>Viloyat / shahar *</span>
          <select name="region" required>${ORDER_REGIONS.map(r => `<option>${r}</option>`).join("")}</select>
        </label>
        <label class="ofield"><span>Tuman / shahar *</span><input name="city" required></label>
      </div>
      <label class="ofield"><span>Manzil (ko'cha, uy) <small>— xarita belgilasangiz shart emas</small></span><input name="address"></label>
      <div class="ofield"><span>Xaritadan belgilash 📍</span>
        <div class="mapwrap">
          <div id="orderMap" class="omap"></div>
          <div class="mapbar">
            <button type="button" class="btn btn--line btn--sm" id="findMe">📍 Meni topish</button>
            <span class="mapcoords" id="mapCoords"></span>
          </div>
        </div>
      </div>
      <div class="ofield"><span>To'lov usuli</span>
        <div class="opay">
          <label><input type="radio" name="pay" value="Naqd / yetkazib berishda" checked> Naqd</label>
          <label><input type="radio" name="pay" value="Plastik karta"> Karta</label>
          <label><input type="radio" name="pay" value="Online to'lov"> Online</label>
        </div>
      </div>
      <label class="ofield"><span>Izoh (kuryer uchun)</span><input name="note" placeholder="Masalan: 2-qavat, lift bor"></label>
      <button class="btn btn--fill btn--full" type="submit" id="orderSubmit">Tasdiqlash · ${fmt(s.t.total)} (oldindan ${fmt(s.t.prepay)})</button>
    </form>`;
  renderPrepayCard();
  loadPayCard();
  bindPromoBtn();
}

function bindPromoBtn(){
  $("#promoBtn")?.addEventListener("click", async () => {
    const code = ($("#promoInput").value || "").trim().toUpperCase();
    const msg = $("#promoMsg");
    if(!code){
      promoState = { code:"", pct:0 };
      msg.textContent = ""; msg.className = "promo__msg";
      refreshOrderTotals(); return;
    }
    if(!ORDER_API_URL){
      msg.textContent = "⛔ Promokod hozircha ishlamaydi";
      msg.className = "promo__msg is-err"; return;
    }
    msg.textContent = "Tekshirilmoqda..."; msg.className = "promo__msg";
    try{
      const r = await fetch(`${ORDER_API_URL.replace(/\/$/, "")}/api/promo?code=${encodeURIComponent(code)}`);
      const j = await r.json();
      if(j && j.ok){
        promoState = { code: j.code || code, pct: j.pct };
        msg.textContent = `✅ ${promoState.pct}% chegirma qo'llandi!`;
        msg.className = "promo__msg is-ok";
      }else{
        promoState = { code:"", pct:0 };
        msg.textContent = "⛔ " + ((j && j.error) || "topilmadi");
        msg.className = "promo__msg is-err";
      }
    }catch(e){
      msg.textContent = "⛔ Tekshirib bo'lmadi, internetni tekshiring";
      msg.className = "promo__msg is-err";
    }
    refreshOrderTotals();
  });
}

async function submitOrderForm(form){
  // (form.name brauzerning ichki xususiyati bilan to'qnashgani uchun querySelector ishlatamiz)
  const val = n => (form.querySelector(`[name="${n}"]`)?.value || "").trim();
  const name = val("name");
  const phone = val("phone");
  const city = val("city");
  const address = val("address");
  if(!name || !phone || !city){ toast("Iltimos, majburiy maydonlarni to'ldiring"); return; }
  if(phone.replace(/\D/g, "").length < 9){ toast("Telefon raqamni to'g'ri kiriting"); form.querySelector('[name="phone"]').focus(); return; }
  const loc = getOrderLoc();
  if(!address && !loc){ toast("Manzilni yozing yoki xaritadan belgilang 📍"); return; }

  const ship = orderShipCost();
  const items = cart.map(c => {
    const p = getP(c.id);
    return { id:c.id, name:p ? p.name : "?", price:p ? p.price : 0, qty:c.qty };
  });
  const t = calcTotals(ship);
  const order = {
    no: "SB-" + Date.now().toString().slice(-6),
    source: "landing",
    name, phone,
    address: `${val("region")}, ${city}${address ? ", " + address : ""}${(!address && loc) ? " (xaritada belgilangan 📍)" : ""}`,
    loc: loc || null,
    ship: "Standart (5 kun)",
    pay: (form.querySelector('input[name="pay"]:checked') || {}).value || "Naqd / yetkazib berishda",
    note: val("note"),
    items,
    promo: promoState.code,
    discount: t.discount,
    discount_pct: promoState.pct,
    subtotal: t.subtotal, shipCost: ship, total: t.total, prepay: t.prepay
  };

  // Avval qaytarish qoidasi — "Tushundim" bosilgach buyurtma olinadi
  pendingOrder = order;
  openPolicy();
}

async function doSubmitLanding(order){
  const btn = $("#orderSubmit");
  const btnTxt = btn ? btn.textContent : "";
  if(btn){ btn.disabled = true; btn.textContent = "Yuborilmoqda..."; }
  const res = await submitOrder(order);
  if(btn){ btn.disabled = false; btn.textContent = btnTxt; }

  if(res.skipped){
    cart = []; saveCart(); renderCart(); closeOrderModal();
    toast(`Buyurtma ${order.no} qabul qilindi ✅ (test rejim)`);
    return;
  }
  if(!res.ok){ toast("Yuborilmadi: " + res.error + ". Qayta urinib ko'ring"); return; }
  cart = []; saveCart(); renderCart();
  // Muvaffaqiyat + botga o'tish (50% to'lov va chek uchun)
  const viaServer = res.via === "server" && res.id;  $("#orderBody").innerHTML = `
    <div class="osuccess">
      <div class="osuccess__icon">✓</div>
      <h2>Buyurtma ${order.no} qabul qilindi!</h2>
      <p>Rahmat, <b>${esc(order.name)}</b>!</p>
      <div class="osum">
        <div class="osum__row"><span>Jami</span><b>${fmt(order.total)}</b></div>
        <div class="osum__row osum__pre"><span>Oldindan 50%</span><b>${fmt(order.prepay)}</b></div>
        <div class="osum__row"><span>Qolgan</span><b>${fmt(order.total - order.prepay)}</b></div>
      </div>
      ${viaServer ? `
      <div class="obotgo">
        <h3>Keyingi qadam — 50% to'lov 💳</h3>
        <p><b>${fmt(order.prepay)}</b> ni to'lang va chekni botga yuboring.</p>
        <a class="btn btn--fill btn--full" href="https://t.me/${BOT_USERNAME}?start=ord_${res.id}" target="_blank" rel="noopener">✈ Botga o'tish va chek yuborish</a>
        <small>Chek tekshirilgach, buyurtma adminga o'tadi.</small>
      </div>` : `<p class="reveal">Tez orada bog'lanamiz.</p>`}
    </div>`;
  // buyurtma modali yopilgan edi (qoida oynasi uchun) — natijani ko'rsatish uchun qayta ochamiz
  $("#orderModal").classList.add("on");
  $("#orderModal").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

const BOT_USERNAME = "samabasicbot";
let pendingOrder = null;

function openPolicy(){
  closeOrderModal();
  $("#policyModal").classList.add("on");
  $("#policyModal").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}
function closePolicy(){
  $("#policyModal").classList.remove("on");
  $("#policyModal").setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}
function openCart(){
  $("#cart").classList.add("on");
  $("#cart").setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}
function closeCart(){
  $("#cart").classList.remove("on");
  $("#cart").setAttribute("aria-hidden", "true");
  if(!$("#modal").classList.contains("on") && !$("#orderModal").classList.contains("on")) document.body.style.overflow = "";
}

// ---------- Reveal animatsiya ----------
let io;
function observeReveals(){
  if(!io){
    io = new IntersectionObserver(entries => {
      entries.forEach(en => { if(en.isIntersecting){ en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold:.12, rootMargin:"0px 0px -60px 0px" });
  }
  $$(".reveal:not(.in)").forEach(el => io.observe(el));
}

// ---------- Hodisalar ----------
$("#grid")?.addEventListener("click", e => {
  const open = e.target.closest("[data-open]");
  const add  = e.target.closest("[data-add]");
  const inc  = e.target.closest("[data-inc]");
  const dec  = e.target.closest("[data-dec]");

  if(open){ openModal(open.dataset.open); return; }
  if(add){
    const id = add.dataset.add;
    const box = $(`[data-q="${id}"]`);
    const v = box ? box.querySelector(`[data-val="${id}"]`) : null;
    if(!v && !isQtyOpen(id)){
      toast("Avval «+» ni bosib sotib olmoqchi bo'lgan narsangizni tanlang");
      return;
    }
    const n = v ? +v.textContent : getCardQty(id);
    addToCart(id, n);
    closeQty(id);
    if(box) box.innerHTML = qtyInner(id);
    return;
  }
  if(inc || dec){
    const id = (inc || dec).dataset.inc || (inc || dec).dataset.dec;
    const box = $(`[data-q="${id}"]`);
    if(!box) return;
    const v = box.querySelector(`[data-val="${id}"]`);
    if(inc){
      if(v) setCardQty(id, +v.textContent + 1);
      else setCardQty(id, 1); // birinchi bosish — stepperni 1 bilan ochish
    }else{
      if(!v) return;
      const cur = +v.textContent;
      if(cur <= 1) closeQty(id); // 1 da "−" — yana faqat "+" ga yig'ish
      else setCardQty(id, cur - 1);
    }
    box.innerHTML = qtyInner(id);
  }
});

$("#tabs")?.addEventListener("click", e => {
  const t = e.target.closest(".tab");
  if(!t) return;
  $$(".tab").forEach(x => x.classList.remove("is-on"));
  t.classList.add("is-on");
  activeCat = t.dataset.cat;
  renderGrid();
});

document.querySelectorAll("[data-jump]").forEach(a => a.addEventListener("click", () => {
  const cat = a.dataset.jump;
  activeCat = cat;
  $$(".tab").forEach(x => x.classList.toggle("is-on", x.dataset.cat === cat));
  renderGrid();
}));

// Modal / savat / buyurtma / qoida yopish
document.addEventListener("click", e => {
  if(e.target.closest("[data-close]")) closeModal();
  if(e.target.closest("[data-cart-close]")) closeCart();
  if(e.target.closest("[data-order-close]")) closeOrderModal();
  if(e.target.closest("[data-polclose]")) closePolicy();
});

// Dinamik buyurtma formasi
document.addEventListener("submit", e => {
  if(e.target && e.target.id === "orderForm"){ e.preventDefault(); submitOrderForm(e.target); }
});

$("#cartOpen")?.addEventListener("click", openCart);

$("#cartBody")?.addEventListener("click", e => {
  const inc = e.target.closest("[data-cinc]");
  const dec = e.target.closest("[data-cdec]");
  const rm  = e.target.closest("[data-crm]");
  if(inc) changeQty(inc.dataset.cinc, 1);
  if(dec) changeQty(dec.dataset.cdec, -1);
  if(rm)  { cart = cart.filter(c => c.id !== +rm.dataset.crm); saveCart(); renderCart(); }
});

$("#orderBtn")?.addEventListener("click", openOrderModal);

$("#policyOk")?.addEventListener("click", async () => {
  if(!pendingOrder) return;
  const order = pendingOrder;
  pendingOrder = null;
  closePolicy();
  await doSubmitLanding(order);
});

// Burger
const menu = $("#menu"), burger = $("#burger");
burger?.addEventListener("click", () => { menu.classList.toggle("on"); burger.classList.toggle("on"); });
menu?.querySelectorAll("a").forEach(a => a.addEventListener("click", () => { menu.classList.remove("on"); burger.classList.remove("on"); }));

// Header scroll holati
addEventListener("scroll", () => $("#top").classList.toggle("scrolled", scrollY > 20));

// ESC
addEventListener("keydown", e => {
  if(e.key === "Escape"){ closeModal(); closeCart(); closeOrderModal(); closePolicy(); menu?.classList.remove("on"); burger?.classList.remove("on"); }
});

// ---------- Boshlash ----------
renderGrid();
renderCart();
observeReveals();
loadServerProducts();
document.addEventListener("products:update", () => { renderGrid(); renderCart(); });
