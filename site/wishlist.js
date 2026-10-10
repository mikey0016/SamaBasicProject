/* =========================================================
   Sama Basic — sevimlilar sahifasi (wishlist)
   ========================================================= */

function renderWishlist(){
  const inner = $("#wishInner");
  if(!inner) return;

  if(!wishlist.length){
    inner.innerHTML = `
      <div class="empty">
        <div class="empty__icon">♡</div>
        <h2>Sevimlilar ro'yxati bo'sh</h2>
        <p>Mahsulotlar ustidagi yurakcha (♡) tugmasini bosib ularni shu yerga saqlang.</p>
        <a href="shop.html" class="btn btn--primary">Do'konga o'tish</a>
      </div>`;
    return;
  }

  const list = wishlist.map(id => getProduct(id)).filter(Boolean).reverse();
  inner.innerHTML = `
    <div class="grid grid--shop" id="wishGrid">
      ${list.map((p, i) => productCardHTML(p, i)).join("")}
    </div>`;
  bindCardEvents($("#wishGrid"));
}

// yurakcha bosilib o'chirilsa — sahifani yangilash
document.addEventListener("wishlist:change", () => {
  setTimeout(renderWishlist, 250);
});

// ---------- Boshlash ----------
mountLayout("shop");
renderWishlist();
document.addEventListener("products:update", renderWishlist);
