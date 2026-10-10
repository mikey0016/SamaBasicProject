/* =========================================================
   Sama Basic — bosh sahifa (home)
   ========================================================= */

const grid = $("#productGrid");

function renderFeatured(){
  if(!grid) return;
  // chegirmali va yangi mahsulotlarni oldinga chiqaramiz
  const list = [...PRODUCTS].sort((a,b) => (b.tag ? 1 : 0) - (a.tag ? 1 : 0)).slice(0, 8);
  grid.innerHTML = list.map((p, i) => productCardHTML(p, i)).join("");
  bindCardEvents(grid);
}

// ---------- Boshlash ----------
mountLayout("home");
renderFeatured();
document.addEventListener("products:update", renderFeatured);
