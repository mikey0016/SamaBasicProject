/* =========================================================
   Sama Basic — aloqa sahifasi (contact)
   ========================================================= */

$("#contactForm")?.addEventListener("submit", e => {
  e.preventDefault();
  const f = e.target;
  if(!f.name.value.trim() || !f.contact.value.trim() || !f.message.value.trim()){
    toast("Iltimos, barcha maydonlarni to'ldiring");
    return;
  }
  toast("Xabaringiz yuborildi! Tez orada javob beramiz ✅");
  f.reset();
});

// ---------- Boshlash ----------
mountLayout("contact");
