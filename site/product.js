/* =========================================================
   Sama Basic — mahsulot sahifasi (product)
   ========================================================= */

const params  = new URLSearchParams(location.search);
let product = getProduct(params.get("id")) || PRODUCTS[0] || null;
if(product && !product.gallery.length){
  // Faqat rang rasmlari bor mahsulot — birinchisidan galereya yig'amiz
  const cg = product.colorGalleries || {};
  const k = Object.keys(cg)[0];
  const a = k ? cg[k] : null;
  product.gallery = (Array.isArray(a) && a.length)
    ? a.map((s, i) => ({ src: s, label: `Ko'rinish ${i + 1}` }))
    : [{ src: "assets/logo.jpg", label: "Rasm yo'q" }];
}

let selectedSize  = null;
let selectedColor = product ? product.colors[0] : null;
let qty           = 1;
let viewIndex     = 0;

// ---------- Breadcrumb ----------
function renderBreadcrumb(){
  const bc = $("#breadcrumb");
  if(!bc || !product) return;
  bc.innerHTML = `
    <a href="index.html">Bosh sahifa</a><span>/</span>
    <a href="shop.html">Do'kon</a><span>/</span>
    <a href="shop.html?cat=${product.cat}">${CATS[product.cat] || product.cat}</a><span>/</span>
    <strong>${product.name}</strong>`;
}

function stars(rating){
  const full = Math.round(rating);
  let s = "";
  for(let i = 1; i <= 5; i++) s += i <= full ? "★" : "☆";
  return s;
}

// ---------- Asosiy blok ----------
function renderProduct(){
  const inner = $("#productInner");
  if(!inner) return;
  if(!product){
    inner.innerHTML = `<div class="empty"><div class="empty__icon">🛍️</div><h2>Mahsulot topilmadi</h2><p>Hozircha do'konda mahsulot yo'q.</p><a href="shop.html" class="btn btn--primary">Do'konga qaytish</a></div>`;
    return;
  }
  viewIndex = 0;
  document.title = `${product.name} — Sama Basic`;

  const discount = discountPct(product);
  const wished = isWished(product.id);

  inner.innerHTML = `
    <div class="gallery">
      <div class="gallery__main">
        <img id="galleryMain" src="${product.gallery[0].src}" alt="${product.name}">
        ${discount ? `<span class="gallery__badge">-${discount}%</span>` : ""}
        <button class="gallery__wish ${wished?'active':''}" id="wishBtn" aria-label="Sevimlilar">${wished?'♥':'♡'}</button>
      </div>
      <div class="gallery__thumbs" id="galleryThumbs">
        ${product.gallery.map((g, i) => `
          <button class="gallery__thumb ${i===0?'is-active':''}" data-view="${i}" aria-label="${g.label}">
            <img src="${g.src}" alt="${g.label}">
          </button>`).join("")}
      </div>
      <div class="gallery__current" id="galleryLabel">${product.gallery[0].label}</div>
    </div>

    <div class="pinfo">
      <p class="pinfo__cat">${CATS[product.cat] || product.cat}</p>
      <h1 class="pinfo__title">${product.name}</h1>

      <div class="pinfo__rating">
        <span class="stars">${stars(product.rating)}</span>
        <span>${product.rating} · ${product.reviews} sharh</span>
        <span class="pinfo__stock ${product.stock > 5 ? 'is-in' : 'is-low'}">
          ${product.stock > 5 ? "Sotuvda mavjud" : `Faqat ${product.stock} dona qoldi`}
        </span>
      </div>

      <div class="pinfo__price">
        <b>${fmt(product.price)}</b>
        ${product.old ? `<s>${fmt(product.old)}</s><span class="pinfo__save">Tejaysiz ${fmt(product.old - product.price)}</span>` : ""}
      </div>

      <p class="pinfo__desc">${product.desc}</p>

      <div class="opt">
        <div class="opt__head"><h4>O'lcham</h4><span>${product.sizes.length > 1 ? "Tanlang" : "Bitta o'lcham"}</span></div>
        <div class="opt__row" id="sizeRow">
          ${product.sizes.map((s, i) => `
            <button class="chip ${product.sizes.length===1 && i===0 ? 'is-active' : ''}" data-size="${s}">${s}</button>`).join("")}
        </div>
      </div>

      <div class="opt">
        <div class="opt__head"><h4>Rang</h4><span id="colorName">${selectedColor}</span></div>
        <div class="opt__row" id="colorRow">
          ${product.colors.map((c, i) => `
            <button class="chip ${i===0?'is-active':''}" data-color="${c}">${c}</button>`).join("")}
        </div>
      </div>

      <div class="buy">
        <div class="qty qty--lg">
          <button class="qty__btn" id="qDec" aria-label="Kamaytirish">−</button>
          <span class="qty__val" id="qVal">1</span>
          <button class="qty__btn" id="qInc" aria-label="Ko'paytirish">+</button>
        </div>
        <button class="btn btn--primary buy__add" id="addBtn">Savatga qo'shish</button>
        <button class="btn btn--ghost buy__now" id="buyNow">Hozir olish</button>
      </div>

      <ul class="pinfo__meta">
        <li><span>Material</span><strong>${product.material}</strong></li>
        <li><span>Parvarish</span><strong>${product.care}</strong></li>
      </ul>

      <div class="acc">
        <details open><summary>Tavsif</summary><p>${product.desc}</p></details>
        <details><summary>Yetkazib berish</summary><p>O'zbekiston bo'ylab maksimal 5 kun ichida yetkazib beriladi. 1 ta mahsulotda yetkazish 40 000 so'm, 2+ da — bepul.</p></details>
        <details><summary>Qaytarish</summary><p>Qaytarish faqat bizning xatolikda: noto'g'ri yoki brak tovar yuborilsa. O'lcham/rang tanlashdagi xatolikka qaytarish yo'q.</p></details>
      </div>
    </div>`;

  bindProductEvents();
}

function setView(i){
  const g = product.gallery[i];
  const main = $("#galleryMain");
  if(!g || !main) return;
  viewIndex = i;
  main.src = g.src;
  main.alt = `${product.name} — ${g.label}`;
  $("#galleryLabel").textContent = g.label;
  $$(".gallery__thumb").forEach((t, idx) => t.classList.toggle("is-active", idx === i));
}

function checkSize(){
  if(product.sizes.length > 1 && !selectedSize){ toast("Iltimos, o'lchamni tanlang"); return false; }
  return true;
}

function bindProductEvents(){
  // Telefonda rasmlar orasida swipe qilish
  const gmain = $(".gallery__main");
  if(gmain){
    let sx = null;
    gmain.addEventListener("touchstart", e => { sx = e.touches[0].clientX; }, { passive: true });
    gmain.addEventListener("touchend", e => {
      if(sx === null) return;
      const dx = e.changedTouches[0].clientX - sx; sx = null;
      const n = product.gallery.length;
      if(n < 2 || Math.abs(dx) < 40) return;
      setView(dx < 0 ? (viewIndex + 1) % n : (viewIndex - 1 + n) % n);
    }, { passive: true });
  }

  $("#galleryThumbs")?.addEventListener("click", e => {
    const t = e.target.closest("[data-view]");
    if(t) setView(+t.dataset.view);
  });

  $("#wishBtn")?.addEventListener("click", () => {
    toggleWish(product.id);
    const on = isWished(product.id);
    const b = $("#wishBtn");
    b.classList.toggle("active", on);
    b.textContent = on ? "♥" : "♡";
  });

  $("#sizeRow")?.addEventListener("click", e => {
    const c = e.target.closest("[data-size]");
    if(!c) return;
    $$("#sizeRow .chip").forEach(x => x.classList.remove("is-active"));
    c.classList.add("is-active");
    selectedSize = c.dataset.size;
  });

  $("#colorRow")?.addEventListener("click", e => {
    const c = e.target.closest("[data-color]");
    if(!c) return;
    $$("#colorRow .chip").forEach(x => x.classList.remove("is-active"));
    c.classList.add("is-active");
    selectedColor = c.dataset.color;
    $("#colorName").textContent = selectedColor;
  });

  $("#qDec")?.addEventListener("click", () => { qty = Math.max(1, qty - 1); $("#qVal").textContent = qty; });
  $("#qInc")?.addEventListener("click", () => { qty++; $("#qVal").textContent = qty; });

  $("#addBtn")?.addEventListener("click", () => { if(checkSize()) addToCart(product.id, qty); });
  $("#buyNow")?.addEventListener("click", () => { if(checkSize()){ addToCart(product.id, qty); openCart(); } });
}

// ---------- O'xshash mahsulotlar ----------
function renderRelated(){
  const grid = $("#relatedGrid");
  if(!grid || !product){
    const sec = $("#related");
    if(sec) sec.style.display = "none";
    return;
  }
  const list = PRODUCTS.filter(p => p.cat === product.cat && p.id !== product.id).slice(0, 4);
  if(!list.length){ $("#related").style.display = "none"; return; }
  grid.innerHTML = list.map((p, i) => productCardHTML(p, i)).join("");
  bindCardEvents(grid);
}

// ---------- Boshlash ----------
mountLayout("shop");
renderBreadcrumb();
renderProduct();
renderRelated();

// Serverdan yangi mahsulot kelganda sahifani yangilash (masalan ?id=1001)
document.addEventListener("products:update", () => {
  const p = getProduct(params.get("id"));
  if(!p || p === product) return;
  product = p;
  selectedSize = null;
  selectedColor = product.colors[0];
  qty = 1;
  renderBreadcrumb();
  renderProduct();
  renderRelated();
  window.scrollTo({ top: 0 });
});
