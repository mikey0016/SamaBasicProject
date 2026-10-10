/* =========================================================
   Sama Basic — umumiy layout (header / footer / drawer / qidiruv)
   Har bir sahifa mountLayout(key) chaqiradi.
   ========================================================= */

const NAV_ITEMS = [
  { href: "index.html",       label: "Bosh sahifa",  key: "home" },
  { href: "shop.html",        label: "Do'kon",       key: "shop" },
  { href: "index.html#about", label: "Biz haqimizda", key: "about" },
  { href: "contact.html",     label: "Aloqa",        key: "contact" },
];

const ICONS = {
  search: `<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M10 2a8 8 0 105.29 14.01l4.35 4.35 1.41-1.41-4.35-4.35A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z"/></svg>`,
  heart:  `<svg viewBox="0 0 24 24" width="21" height="21"><path fill="currentColor" d="M12 21s-7.5-4.8-9.7-9A5.2 5.2 0 0112 5.6 5.2 5.2 0 0121.7 12c-2.2 4.2-9.7 9-9.7 9z"/></svg>`,
  cart:   `<svg viewBox="0 0 24 24" width="21" height="21"><path fill="currentColor" d="M7 4h-2l-1 2H2v2h2l2.6 9.6A2 2 0 008.5 19h9a2 2 0 002-1.6L22 8H6l.7 2H19.4l-1.7 6H8.6L7 4zM9 20.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zm9 0a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"/></svg>`,
  user:   `<svg viewBox="0 0 24 24" width="21" height="21"><path fill="currentColor" d="M12 12a5 5 0 100-10 5 5 0 000 10zm0 2c-4.4 0-8 2.7-8 6v2h16v-2c0-3.3-3.6-6-8-6z"/></svg>`,
};

function headerHTML(active){
  const nav = NAV_ITEMS.map(n =>
    `<a href="${n.href}" class="${n.key === active ? 'is-active' : ''}">${n.label}</a>`).join("");

  return `
  <div class="topbar">
    <span>Butun O'zbekiston bo'ylab yetkazib berish</span>
    <span class="topbar__right">Instagram: <a href="https://www.instagram.com/sama_basic" target="_blank" rel="noopener">@sama_basic</a></span>
  </div>

  <header class="header" id="header">
    <div class="container header__inner">
      <a href="index.html" class="brand">
        <img src="assets/logo.jpg" alt="Sama Basic logo" class="brand__logo">
        <span class="brand__name">Sama <span>Basic</span></span>
      </a>

      <nav class="nav" id="nav">
        ${nav}
        <div class="nav__mobile">
          <a href="wishlist.html">Sevimlilar</a>
          <a href="cart.html">Savat</a>
          <a href="login.html">Kirish</a>
          <a href="register.html">Ro'yxatdan o'tish</a>
        </div>
      </nav>

      <div class="header__actions">
        <button class="icon-btn" id="searchBtn" aria-label="Qidirish">${ICONS.search}</button>

        <a class="icon-btn" href="wishlist.html" aria-label="Sevimlilar" title="Sevimlilar">
          ${ICONS.heart}
          <span class="cart-count wish-count" id="wishCount">0</span>
        </a>

        <div class="account-area" id="accountArea"></div>

        <button class="icon-btn cart-btn" id="cartBtn" aria-label="Savat">
          ${ICONS.cart}
          <span class="cart-count" id="cartCount">0</span>
        </button>

        <button class="burger" id="burger" aria-label="Menyu"><span></span><span></span><span></span></button>
      </div>
    </div>
  </header>`;
}

function footerHTML(){
  return `
  <footer class="footer" id="contact">
    <div class="container footer__inner">
      <div class="footer__brand">
        <img src="assets/logo.jpg" alt="Sama Basic" class="brand__logo">
        <p>Sama Basic — kiyimlar va aksessuarlar do'koni. Asosiy narsalar, mukammal uslub.</p>
      </div>
      <div class="footer__col">
        <h4>Do'kon</h4>
        <a href="shop.html">Barcha mahsulotlar</a>
        <a href="shop.html?cat=kiyimlar">Kiyimlar</a>
        <a href="shop.html?cat=aksessuarlar">Aksessuarlar</a>
        <a href="wishlist.html">Sevimlilar</a>
      </div>
      <div class="footer__col">
        <h4>Yordam</h4>
        <a href="cart.html">Savat</a>
        <a href="checkout.html">Buyurtma berish</a>
        <a href="login.html">Hisobim</a>
        <a href="contact.html">Aloqa</a>
      </div>
      <div class="footer__col">
        <h4>Aloqa</h4>
        <a href="https://www.instagram.com/sama_basic" target="_blank" rel="noopener">Instagram @sama_basic</a>
        <a href="https://t.me/para_kiyim_parnie_futbolki" target="_blank" rel="noopener">Telegram kanal ✈</a>
        <a href="tel:+998900000000">+998 90 000 00 00</a>
        <span>Toshkent, O'zbekiston</span>
      </div>
    </div>
    <div class="container footer__bottom">
      <span>© 2026 Sama Basic. Barcha huquqlar himoyalangan.</span>
      <span>Asosiy rang: olive #343c24</span>
    </div>
  </footer>`;
}

function drawerHTML(){
  return `
  <div class="drawer-overlay" id="overlay"></div>
  <aside class="drawer" id="cartDrawer">
    <div class="drawer__head">
      <h3>Savat</h3>
      <button class="icon-btn" id="closeCart" aria-label="Yopish">✕</button>
    </div>
    <div class="drawer__body" id="cartItems"></div>
    <div class="drawer__foot">
      <div class="drawer__total"><span>Jami:</span><strong id="cartTotal">0 so'm</strong></div>
      <button class="btn btn--primary btn--block" id="checkout">Buyurtma berish</button>
      <a class="drawer__link" href="cart.html">Savat sahifasiga o'tish →</a>
    </div>
  </aside>

  <div class="searchbar" id="searchBar">
    <div class="container searchbar__inner">
      <input type="text" id="searchInput" placeholder="Mahsulot qidirish... (Enter)">
      <button class="icon-btn" id="closeSearch">✕</button>
    </div>
  </div>

  <div class="toast" id="toast"></div>`;
}

function mountLayout(active){
  const h = document.getElementById("siteHeader");
  const f = document.getElementById("siteFooter");
  if(h) h.innerHTML = headerHTML(active);
  if(f) f.innerHTML = footerHTML();
  document.body.insertAdjacentHTML("beforeend", drawerHTML());

  initCommonUI();

  // Qidiruv
  const bar = $("#searchBar");
  $("#searchBtn")?.addEventListener("click", () => { bar.classList.add("open"); $("#searchInput").focus(); });
  $("#closeSearch")?.addEventListener("click", () => bar.classList.remove("open"));
  $("#searchInput")?.addEventListener("keydown", e => {
    if(e.key === "Enter"){
      const v = e.target.value.trim();
      location.href = "shop.html" + (v ? `?q=${encodeURIComponent(v)}` : "");
    }
  });
}
