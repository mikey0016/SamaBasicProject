/* =========================================================
   Sama Basic — buyurtma sahifasi (checkout)
   ========================================================= */

const SHIP_ONE = 40000; // 1 dona olsa — yetkazish pulli
const EXPRESS_EXTRA = 20000;

// Qoida: 2+ dona → bepul, 1 dona → 40 000
function baseShipCost(){ return cartCount() >= 2 ? 0 : SHIP_ONE; }

const REGIONS = ["Toshkent shahri","Toshkent viloyati","Samarqand","Buxoro","Andijon","Farg'ona","Namangan","Qashqadaryo","Surxondaryo","Xorazm","Navoiy","Jizzax","Sirdaryo","Qoraqalpog'iston"];

let promoState = { code:"", pct:0 };

function calcTotals(ship){
  const subtotal = cartTotal();
  const discount = promoState.pct ? Math.round(subtotal * promoState.pct / 100) : 0;
  const total = subtotal - discount + ship;
  return { subtotal, discount, total, prepay: Math.round(total / 2) };
}

function summaryHTML(shipCost){
  const t = calcTotals(shipCost);
  return `
    <h3>Buyurtma xulosasi</h3>
    <div class="sum__items">
      ${cart.map(c => {
        const p = getProduct(c.id); if(!p) return "";
        return `<div class="sum__item">
          <img src="${p.img}" alt="${p.name}">
          <div><span>${p.name}</span><small>${c.qty} × ${fmt(p.price)}</small></div>
          <b>${fmt(p.price * c.qty)}</b>
        </div>`;
      }).join("")}
    </div>
    <div class="sum__row"><span>Mahsulotlar</span><strong>${fmt(t.subtotal)}</strong></div>
    ${t.discount ? `<div class="sum__row sum__row--disc"><span>Promokod ${escHtml(promoState.code)} (-${promoState.pct}%)</span><strong>−${fmt(t.discount)}</strong></div>` : ""}
    <div class="sum__row"><span>Yetkazib berish</span><strong>${shipCost ? fmt(shipCost) : "Bepul"}</strong></div>
    <div class="sum__row sum__row--total"><span>Jami</span><strong>${fmt(t.total)}</strong></div>
    <div class="sum__row sum__row--prepay"><span>Oldindan 50%</span><strong>${fmt(t.prepay)}</strong></div>
    <div class="sum__row"><span>Qolgan (yetkazishda)</span><strong>${fmt(t.total - t.prepay)}</strong></div>
    <p class="sum__secure">🔒 Ma'lumotlaringiz xavfsiz saqlanadi</p>`;
}

function renderCheckout(){
  const inner = $("#checkoutInner");
  if(!inner) return;

  if(!cart.length){
    inner.innerHTML = `
      <div class="empty">
        <div class="empty__icon">🧾</div>
        <h2>Buyurtma berish uchun savat bo'sh</h2>
        <p>Avval mahsulot tanlang, keyin bu yerga qaytib keling.</p>
        <a href="shop.html" class="btn btn--primary">Do'konga o'tish</a>
      </div>`;
    return;
  }

  const subtotal = cartTotal();
  const baseShip = baseShipCost();

  inner.innerHTML = `
    <form class="checkout__form" id="orderForm" novalidate>
      <h3 class="form__title">Aloqa ma'lumotlari</h3>
      <div class="form__grid">
        <label class="field"><span>Ism *</span><input name="first" required value="${user?.name?.split(" ")[0] || ""}"></label>
        <label class="field"><span>Familiya *</span><input name="last" required></label>
        <label class="field field--full"><span>Telefon *</span><input name="phone" required placeholder="+998 __ ___ __ __"></label>
      </div>

      <h3 class="form__title">Yetkazib berish manzili</h3>
      <div class="form__grid">
        <label class="field"><span>Viloyat / shahar *</span>
          <select name="region" required>${REGIONS.map(r => `<option>${r}</option>`).join("")}</select>
        </label>
        <label class="field"><span>Tuman / shahar nomi *</span><input name="city" required></label>
        <label class="field field--full"><span>Manzil (ko'cha, uy) <small class="field__hint">— xaritada belgilasangiz shart emas</small></span><input name="address"></label>
        <div class="field field--full">
          <span class="field__label">Xaritadan belgilash 📍</span>
          <div class="mapwrap">
            <div id="orderMap" class="omap"></div>
            <div class="mapbar">
              <button type="button" class="btn btn--ghost btn--sm" id="findMe">📍 Meni topish</button>
              <span class="mapcoords" id="mapCoords"></span>
            </div>
          </div>
        </div>
        <label class="field field--full"><span>Izoh (kuryer uchun)</span><input name="note" placeholder="Masalan: 2-qavat, lift bor"></label>
      </div>

      <h3 class="form__title">Yetkazib berish usuli</h3>
      <div class="opt__list">
        <label class="radio radio--card">
          <input type="radio" name="ship" value="standard" checked>
          <span><b>Standart</b><small>5 kun ichida · ${baseShip ? fmt(baseShip) : "Bepul"}</small></span>
        </label>
        <label class="radio radio--card">
          <input type="radio" name="ship" value="express">
          <span><b>Tezkor</b><small>24 soat ichida · ${fmt(baseShip + EXPRESS_EXTRA)}</small></span>
        </label>
      </div>
      <p class="form__hint">📦 1 ta mahsulotda yetkazish 40 000 so'm, 2+ da — bepul. Maksimal 5 kunda yetkaziladi.</p>

      <h3 class="form__title">Promokod (% li chegirma)</h3>
      <div class="promo">
        <input id="promoInput" placeholder="Promokodni kiriting" autocomplete="off">
        <button type="button" class="btn btn--ghost" id="promoBtn">Qo'llash</button>
      </div>
      <p class="promo__msg" id="promoMsg"></p>

      <h3 class="form__title">Boshlang'ich to'lov — 50%</h3>
      <div class="prepay" id="prepayBox"></div>

      <h3 class="form__title">To'lov usuli</h3>
      <div class="opt__list">
        <label class="radio radio--card"><input type="radio" name="pay" value="cash" checked><span><b>Naqd / yetkazib berishda</b><small>Kuryerga naqd to'lov</small></span></label>
        <label class="radio radio--card"><input type="radio" name="pay" value="card"><span><b>Plastik karta</b><small>Yetkazib berishda terminal</small></span></label>
        <label class="radio radio--card"><input type="radio" name="pay" value="online"><span><b>Online to'lov</b><small>Payme / Click</small></span></label>
      </div>

      <button type="submit" class="btn btn--primary btn--block checkout__submit">Buyurtmani tasdiqlash</button>
    </form>

    <aside class="cart__summary" id="checkoutSummary">${summaryHTML(baseShip)}</aside>`;

  initOrderMap();
  bindCheckout(baseShip);
}

let curBase = 0;
let payCard = "";
let pendingOrder = null;

function openPolicy(){
  $("#policyModal")?.classList.add("on");
  $("#policyModal")?.setAttribute("aria-hidden", "false");
}
function closePolicy(){
  $("#policyModal")?.classList.remove("on");
  $("#policyModal")?.setAttribute("aria-hidden", "true");
}

function shipNow(){
  const exp = document.querySelector('input[name="ship"]:checked')?.value === "express";
  return exp ? curBase + EXPRESS_EXTRA : curBase;
}

function refreshSummary(){
  $("#checkoutSummary").innerHTML = summaryHTML(shipNow());
  renderPrepay();
}

function renderPrepay(){
  const box = $("#prepayBox");
  if(!box) return;
  const t = calcTotals(shipNow());
  box.innerHTML = `
    <div class="prepay__head">
      <span class="prepay__label">Oldindan to'lov · 50%</span>
      <strong class="prepay__big">${fmt(t.prepay)}</strong>
      <span class="prepay__rest">Qolgan <b>${fmt(t.total - t.prepay)}</b> yetkazib berishda to'lanadi</span>
    </div>
    ${payCard
      ? `<p class="prepay__card">💳 To'lov kartasi (Click/Payme): <b>${payCard}</b><br><small>To'lov chekini saqlang — operator tasdiqlaydi.</small></p>`
      : `<p class="prepay__card">💳 To'lov kartasi: operatorimiz sizga shu chat orqali yuboradi.</p>`}`;
}

async function loadPayCard(){
  if(!ORDER_API_URL) return;
  try{
    const r = await fetch(ORDER_API_URL.replace(/\/$/, "") + "/api/config");
    const j = await r.json();
    if(j && j.ok && j.card){ payCard = j.card; renderPrepay(); }
  }catch(e){}
}

function bindCheckout(baseShip){
  curBase = baseShip;
  renderPrepay();
  loadPayCard();

  // yetkazib berish usuli o'zgarsa xulosani yangilash
  $$('input[name="ship"]').forEach(r => r.addEventListener("change", refreshSummary));

  $("#promoBtn")?.addEventListener("click", async () => {
    const code = ($("#promoInput").value || "").trim().toUpperCase();
    const msg = $("#promoMsg");
    if(!code){
      promoState = { code:"", pct:0 };
      msg.textContent = ""; msg.className = "promo__msg";
      refreshSummary(); return;
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
    refreshSummary();
  });

  $("#orderForm")?.addEventListener("submit", async e => {
    e.preventDefault();
    const form = e.target;
    // validatsiya (querySelector — form.x to'qnashuvlardan holi)
    const q = n => (form.querySelector(`[name="${n}"]`)?.value || "").trim();
    for(const n of ["first","last","phone","city"]){
      if(!q(n)){
        toast("Iltimos, majburiy maydonlarni to'ldiring");
        form.querySelector(`[name="${n}"]`).focus();
        return;
      }
    }
    if(q("phone").replace(/\D/g, "").length < 9){
      toast("Telefon raqamni to'g'ri kiriting");
      form.querySelector('[name="phone"]').focus();
      return;
    }
    const addr = q("address");
    const loc = getOrderLoc();
    if(!addr && !loc){
      toast("Manzilni yozing yoki xaritadan belgilang 📍");
      form.querySelector('[name="address"]').focus();
      return;
    }

    const ship = shipNow();
    const shipMap = { standard: "Standart (5 kun)", express: "Tezkor (24 soat)" };
    const payMap = { cash: "Naqd / yetkazib berishda", card: "Plastik karta", online: "Online to'lov" };
    const items = cart.map(c => {
      const p = getProduct(c.id);
      return { id:c.id, name:p ? p.name : "?", price:p ? p.price : 0, qty:c.qty };
    });
    const t = calcTotals(ship);
    const order = {
      no: "SB-" + Date.now().toString().slice(-6),
      source: "site",
      name: `${q("first")} ${q("last")}`,
      phone: q("phone"),
      address: `${q("region")}, ${q("city")}${addr ? ", " + addr : ""}${(!addr && loc) ? " (xaritada belgilangan 📍)" : ""}`,
      loc: loc || null,
      ship: shipMap[form.querySelector('input[name="ship"]:checked').value],
      pay: payMap[form.querySelector('input[name="pay"]:checked').value],
      note: q("note"),
      items,
      promo: promoState.code,
      discount: t.discount,
      discount_pct: promoState.pct,
      subtotal: t.subtotal,
      shipCost: ship,
      total: t.total,
      prepay: t.prepay
    };

    // Avval qaytarish qoidasi — "Tushundim" bosilgach buyurtma olinadi
    pendingOrder = { order, form };
    openPolicy();
  });

  document.addEventListener("click", e => {
    if(e.target.closest("[data-polclose]")) closePolicy();
  });
  document.addEventListener("keydown", e => {
    if(e.key === "Escape") closePolicy();
  });
  $("#policyOk")?.addEventListener("click", async () => {
    if(!pendingOrder) return;
    const { order, form } = pendingOrder;
    pendingOrder = null;
    closePolicy();
    await doSubmitOrder(order, form);
  });
}

async function doSubmitOrder(order, form){
  const btn = form.querySelector('[type="submit"]');
  btn.disabled = true;
  btn.textContent = "Yuborilmoqda...";
  const res = await submitOrder(order);
  btn.disabled = false;
  btn.textContent = "Buyurtmani tasdiqlash";

  if(!res.ok && !res.skipped){
    toast("Yuborilmadi: " + res.error + ". Qayta urinib ko'ring");
    return;
  }
  const viaServer = res.via === "server" && res.id;
  showSuccess(order,
    res.skipped
      ? "Eslatma: Telegram bot ulanmagan (test rejim)."
      : viaServer
        ? "Buyurtma saqlandi ✓ Endi 50% to'lov uchun botga o'ting."
        : "Buyurtma adminga Telegram orqali yuborildi ✓",
    viaServer ? { id: res.id } : null);
  clearCart();
}

const BOT_USERNAME = "samabasicbot";

function showSuccess(order, status, bot){
  const inner = $("#checkoutInner");
  inner.innerHTML = `
    <div class="success">
      <div class="success__icon">✓</div>
      <h2>Buyurtmangiz qabul qilindi!</h2>
      <p>Rahmat, <b>${order.name}</b>. Operatorimiz tez orada <b>${order.phone}</b> raqamiga bog'lanadi.</p>
      ${status ? `<p class="success__status">${status}</p>` : ""}
      <div class="success__box">
        <div><span>Buyurtma raqami</span><strong>${order.no}</strong></div>
        <div><span>Manzil</span><strong>${order.address}</strong></div>
        <div><span>To'lov</span><strong>${order.pay}</strong></div>
        ${order.promo ? `<div><span>Promokod ${order.promo}</span><strong>−${order.discount_pct}%</strong></div>` : ""}
        <div><span>Jami</span><strong>${fmt(order.total)}</strong></div>
        <div><span>Oldindan 50%</span><strong>${fmt(order.prepay)}</strong></div>
        <div><span>Qolgan</span><strong>${fmt(order.total - order.prepay)}</strong></div>
      </div>
      ${bot ? `
      <div class="botgo">
        <h3>Keyingi qadam — 50% to'lov 💳</h3>
        <p><b>${fmt(order.prepay)}</b> ni to'lang va chekni botga yuboring.</p>
        <a class="btn btn--primary btn--block" href="https://t.me/${BOT_USERNAME}?start=ord_${bot.id}" target="_blank" rel="noopener">✈ Botga o'tish va chek yuborish</a>
        <small>Chek tekshirilgach, buyurtma adminga o'tadi.</small>
      </div>` : ""}
      <div class="success__actions">
        <a href="shop.html" class="btn btn--primary">Xaridni davom ettirish</a>
        <a href="index.html" class="btn btn--ghost">Bosh sahifa</a>
      </div>
    </div>`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ---------- Boshlash ----------
mountLayout("shop");
renderCheckout();
// Bot orqali qo'shilgan mahsulotlar kelganda (savatda bo'lsa) yangilash
document.addEventListener("products:update", () => {
  if(!$("#policyModal")?.classList.contains("on") && $("#orderForm")) renderCheckout();
});
