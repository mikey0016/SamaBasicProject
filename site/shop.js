/* =========================================================
   Sama Basic — do'kon (shop) sahifasi
   ========================================================= */

const urlP = new URLSearchParams(location.search);

const PAGE_SIZE = 6;

const state = {
  cat: urlP.get("cat") || "all",
  q: urlP.get("q") || "",
  min: null,
  max: null,
  colors: [],
  sizes: [],
  saleOnly: false,
  sort: "default",
  page: Math.max(1, +urlP.get("page") || 1),
};

const grid = $("#productGrid");

// ---------- Filtr chiplarini qurish ----------
function buildFilterChips(){
  const colors = [...new Set(PRODUCTS.flatMap(p => p.colors))].sort();
  const sizes  = [...new Set(PRODUCTS.flatMap(p => p.sizes))];

  const cEl = $("#colorFilter");
  if(cEl) cEl.innerHTML = colors.map(c =>
    `<button class="chip chip--sm" data-color="${c}">${c}</button>`).join("");

  const sEl = $("#sizeFilter");
  if(sEl) sEl.innerHTML = sizes.map(s =>
    `<button class="chip chip--sm" data-size="${s}">${s}</button>`).join("");
}

// ---------- Filtrlash + saralash ----------
function getList(){
  let list = PRODUCTS.filter(p => {
    if(state.cat !== "all" && p.cat !== state.cat) return false;
    if(state.q && !p.name.toLowerCase().includes(state.q.toLowerCase())) return false;
    if(state.min !== null && p.price < state.min) return false;
    if(state.max !== null && p.price > state.max) return false;
    if(state.saleOnly && !p.old) return false;
    if(state.colors.length && !state.colors.some(c => p.colors.includes(c))) return false;
    if(state.sizes.length && !state.sizes.some(s => p.sizes.includes(s))) return false;
    return true;
  });

  switch(state.sort){
    case "price-asc":  list.sort((a,b) => a.price - b.price); break;
    case "price-desc": list.sort((a,b) => b.price - a.price); break;
    case "rating":     list.sort((a,b) => b.rating - a.rating); break;
    case "name":       list.sort((a,b) => a.name.localeCompare(b.name)); break;
  }
  return list;
}

function renderShop(){
  const list = getList();
  const cnt = $("#resultCount");
  const pager = $("#pager");

  if(!list.length){
    if(cnt) cnt.textContent = "0 ta mahsulot";
    grid.innerHTML = `<p class="grid__empty">Filtrga mos mahsulot topilmadi.<br>Filtrlarni tozalab ko'ring.</p>`;
    if(pager) pager.innerHTML = "";
    return;
  }

  const pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
  state.page = Math.min(Math.max(1, state.page), pages);
  const start = (state.page - 1) * PAGE_SIZE;
  const slice = list.slice(start, start + PAGE_SIZE);

  if(cnt) cnt.textContent = `${start + 1}–${start + slice.length} / ${list.length} ta mahsulot`;
  grid.innerHTML = slice.map((p, i) => productCardHTML(p, i)).join("");
  bindCardEvents(grid);
  renderPager(pages);
}

function pageNums(cur, total){
  if(total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set([1, 2, cur - 1, cur, cur + 1, total - 1, total].filter(n => n >= 1 && n <= total));
  const arr = [...set].sort((a, b) => a - b);
  const out = [];
  arr.forEach((n, i) => {
    if(i && n - arr[i - 1] > 1) out.push("…");
    out.push(n);
  });
  return out;
}

function renderPager(pages){
  const pager = $("#pager");
  if(!pager) return;
  if(pages <= 1){ pager.innerHTML = ""; return; }
  pager.innerHTML =
    `<button data-page="prev" ${state.page === 1 ? "disabled" : ""} aria-label="Oldingi">←</button>` +
    pageNums(state.page, pages).map(n =>
      n === "…" ? `<span class="pager__dots">…</span>`
                 : `<button data-page="${n}" class="${n === state.page ? "is-active" : ""}">${n}</button>`
    ).join("") +
    `<button data-page="next" ${state.page === pages ? "disabled" : ""} aria-label="Keyingi">→</button>`;
}

function goPage(p, pages){
  const next = p === "prev" ? state.page - 1 : p === "next" ? state.page + 1 : +p;
  if(!next || next === state.page) return;
  state.page = Math.min(Math.max(1, next), pages);
  renderShop();
  $("#productGrid")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

// ---------- Hodisalar ----------
$("#pager")?.addEventListener("click", e => {
  const b = e.target.closest("[data-page]");
  if(!b || b.disabled) return;
  goPage(b.dataset.page === "prev" ? "prev" : b.dataset.page === "next" ? "next" : +b.dataset.page,
         Math.max(1, Math.ceil(getList().length / PAGE_SIZE)));
});

$("#catFilter")?.addEventListener("change", e => {
  state.cat = e.target.value;
  state.page = 1;
  renderShop();
});

$("#minPrice")?.addEventListener("input", e => { state.min = e.target.value ? +e.target.value : null; state.page = 1; renderShop(); });
$("#maxPrice")?.addEventListener("input", e => { state.max = e.target.value ? +e.target.value : null; state.page = 1; renderShop(); });
$("#saleOnly")?.addEventListener("change", e => { state.saleOnly = e.target.checked; state.page = 1; renderShop(); });
$("#sortBy")?.addEventListener("change", e => { state.sort = e.target.value; state.page = 1; renderShop(); });

$("#colorFilter")?.addEventListener("click", e => {
  const c = e.target.closest("[data-color]");
  if(!c) return;
  const val = c.dataset.color;
  c.classList.toggle("is-active");
  state.colors = c.classList.contains("is-active")
    ? [...state.colors, val] : state.colors.filter(x => x !== val);
  state.page = 1;
  renderShop();
});

$("#sizeFilter")?.addEventListener("click", e => {
  const c = e.target.closest("[data-size]");
  if(!c) return;
  const val = c.dataset.size;
  c.classList.toggle("is-active");
  state.sizes = c.classList.contains("is-active")
    ? [...state.sizes, val] : state.sizes.filter(x => x !== val);
  state.page = 1;
  renderShop();
});

$("#clearFilters")?.addEventListener("click", () => {
  state.cat = "all"; state.q = ""; state.min = null; state.max = null;
  state.colors = []; state.sizes = []; state.saleOnly = false; state.sort = "default";
  $$("#catFilter input").forEach(i => i.checked = i.value === "all");
  $("#minPrice").value = ""; $("#maxPrice").value = "";
  $("#saleOnly").checked = false; $("#sortBy").value = "default";
  $$("#colorFilter .chip, #sizeFilter .chip").forEach(c => c.classList.remove("is-active"));
  state.page = 1;
  renderShop();
});

// Mobil filtr paneli
$("#openFilters")?.addEventListener("click", () => $("#filtersPanel").classList.toggle("open"));

// ---------- Boshlash ----------
mountLayout("shop");
buildFilterChips();
document.querySelector(`#catFilter input[value="${state.cat}"]`)?.setAttribute("checked", "checked");
renderShop();
document.addEventListener("products:update", () => {
  buildFilterChips();
  renderShop();
});
