/* =========================================================
   Sama Basic — savat sahifasi (cart)
   ========================================================= */

const SHIP_ONE = 40000; // 1 dona olsa — pulli, 2+ dona — bepul

function cartShip(){
  return cartCount() >= 2 ? 0 : SHIP_ONE;
}

function renderPage(){
  const inner = $("#cartInner");
  if(!inner) return;

  if(!cart.length){
    inner.innerHTML = `
      <div class="empty">
        <div class="empty__icon">🛍️</div>
        <h2>Savat hozircha bo'sh</h2>
        <p>Do'kondan o'zingizga yoqqan mahsulotni tanlang.</p>
        <a href="shop.html" class="btn btn--primary">Do'konga o'tish</a>
      </div>`;
    return;
  }

  const subtotal = cartTotal();
  const shipping = cartShip();
  const total = subtotal + shipping;

  inner.innerHTML = `
    <div class="cart__list">
      ${cart.map(c => {
        const p = getProduct(c.id);
        if(!p) return "";
        return `
        <article class="cline">
          <a class="cline__img" href="product.html?id=${p.id}"><img src="${p.img}" alt="${p.name}"></a>
          <div class="cline__info">
            <p class="cline__cat">${CATS[p.cat] || p.cat}</p>
            <h3><a href="product.html?id=${p.id}">${p.name}</a></h3>
            <p class="cline__unit">${fmt(p.price)} / dona</p>
          </div>
          <div class="cline__qty">
            <div class="qty">
              <button class="qty__btn" data-dec="${p.id}">−</button>
              <span class="qty__val">${c.qty}</span>
              <button class="qty__btn" data-inc="${p.id}">+</button>
            </div>
          </div>
          <div class="cline__sum">${fmt(p.price * c.qty)}</div>
          <button class="cline__remove" data-remove="${p.id}" aria-label="O'chirish">🗑</button>
        </article>`;
      }).join("")}
    </div>

    <aside class="cart__summary">
      <h3>Buyurtma xulosasi</h3>
      <div class="sum__row"><span>Mahsulotlar (${cartCount()})</span><strong>${fmt(subtotal)}</strong></div>
      <div class="sum__row"><span>Yetkazib berish</span><strong>${shipping ? fmt(shipping) : "Bepul"}</strong></div>
      ${shipping ? `<p class="sum__hint">Yana 1 ta mahsulot qo'shsangiz yetkazish bepul bo'ladi</p>` : ""}
      <div class="sum__row sum__row--total"><span>Jami</span><strong>${fmt(total)}</strong></div>
      <a href="checkout.html" class="btn btn--primary btn--block" data-checkout-btn>Buyurtmani rasmiylashtirish</a>
      <a href="shop.html" class="btn btn--ghost btn--block">Xaridni davom ettirish</a>
    </aside>`;
}

function bindPage(){
  $("#cartInner")?.addEventListener("click", e => {
    const inc = e.target.closest("[data-inc]");
    const dec = e.target.closest("[data-dec]");
    const rm  = e.target.closest("[data-remove]");
    const checkout = e.target.closest("[data-checkout-btn]");

    if(checkout && !cart.length){
      e.preventDefault();
      toast("Savat bo'sh, avval mahsulot tanlang");
      return;
    }

    if(inc) changeQty(+inc.dataset.inc, 1);
    if(dec) changeQty(+dec.dataset.dec, -1);
    if(rm)  removeItem(+rm.dataset.remove);
  });

  document.addEventListener("cart:change", renderPage);
  document.addEventListener("products:update", renderPage);
}

// ---------- Boshlash ----------
mountLayout("shop");
bindPage();
renderPage();
