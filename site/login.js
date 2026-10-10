/* =========================================================
   Sama Basic — kirish / ro'yxatdan o'tish (login)
   ========================================================= */

const nextUrl = new URLSearchParams(location.search).get("next") || "index.html";

// Agar allaqachon kirgan bo'lsa
if(user){
  setTimeout(() => toast(`Siz ${user.name || user.email} sifatida kirgansiz`), 300);
}

// ---------- Kirish (login.html) ----------
$("#loginForm")?.addEventListener("submit", e => {
  e.preventDefault();
  const f = e.target;
  const email = (f.querySelector('[name="email"]')?.value || "").trim();
  setUser({ name: email.split("@")[0], email });
  toast("Muvaffaqiyatli kirdingiz ✅");
  setTimeout(() => location.href = nextUrl, 700);
});

// ---------- Ro'yxatdan o'tish (register.html) ----------
$("#registerForm")?.addEventListener("submit", e => {
  e.preventDefault();
  const f = e.target;
  // (form.name brauzerning ichki xususiyati bilan to'qnashgani uchun querySelector)
  const q = n => (f.querySelector(`[name="${n}"]`)?.value || "").trim();
  setUser({ name: q("name"), email: q("email"), phone: q("phone") });
  toast("Hisob yaratildi! Rahmat 🎉");
  setTimeout(() => location.href = nextUrl, 700);
});

// ---------- Boshlash ----------
mountLayout("home");
