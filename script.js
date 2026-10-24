// Lokal kompyuterda http://127.0.0.1:5000 ga, Vercel'da esa o'z domeniga (/api/...) ulanadi
const API_BASE =
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "localhost" ||
    window.location.protocol === "file:"
        ? "http://127.0.0.1:5000"
        : "";

// Mashinalar ro'yxati
const CARS = [
    {
        id: 1,
        name: "Chevrolet Malibu 2 Premier",
        category: "chevrolet",
        tag: "Chevrolet",
        price: "$31,900",
        year: "2024",
        km: "0 km",
        fuel: "2.0L Turbo",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 2,
        name: "BYD Song Plus DM-i Champion",
        category: "electro",
        tag: "Gibrid",
        price: "$28,500",
        year: "2025",
        km: "0 km",
        fuel: "Gibrid (110 km EV)",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1617788138017-80ad40651399?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 3,
        name: "Chevrolet Cobalt Midnight",
        category: "chevrolet",
        tag: "Bestseller",
        price: "$12,800",
        year: "2025",
        km: "0 km",
        fuel: "1.5L Benzin",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 4,
        name: "Zeekr 001 YOU Edition AWD",
        category: "electro",
        tag: "Elektromobil",
        price: "$46,000",
        year: "2025",
        km: "0 km",
        fuel: "Elektro (656 km)",
        gear: "Avtomat 4WD",
        img: "https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 5,
        name: "Chevrolet Tracker 2 Redline",
        category: "chevrolet",
        tag: "Krossover",
        price: "$19,400",
        year: "2025",
        km: "0 km",
        fuel: "1.2L Turbo",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 6,
        name: "BMW M5 Competition",
        category: "premium",
        tag: "Premium",
        price: "$115,000",
        year: "2024",
        km: "4,200 km",
        fuel: "4.4L V8 Twin-Turbo",
        gear: "M Steptronic",
        img: "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 7,
        name: "LiXiang L9 Ultra",
        category: "premium",
        tag: "Premium SUV",
        price: "$62,000",
        year: "2025",
        km: "0 km",
        fuel: "Gibrid AWD",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 8,
        name: "Chevrolet Gentra Lacetti Elegant",
        category: "chevrolet",
        tag: "Chevrolet",
        price: "$14,900",
        year: "2024",
        km: "1,500 km",
        fuel: "1.5L Benzin/Metan",
        gear: "Avtomat",
        img: "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=800&q=80"
    },
    {
        id: 9,
        name: "Mercedes-Benz AMG G63",
        category: "premium",
        tag: "VIP",
        price: "$245,000",
        year: "2024",
        km: "0 km",
        fuel: "4.0L V8 Biturbo",
        gear: "9G-Tronic",
        img: "https://images.unsplash.com/photo-1520031441872-265e4ff70366?auto=format&fit=crop&w=800&q=80"
    }
];

// DOM elementlar
const authScreen = document.getElementById("authScreen");
const mainSite = document.getElementById("mainSite");

const carsGrid = document.getElementById("carsGrid");
const searchInput = document.getElementById("searchInput");
const filterBtns = document.querySelectorAll(".filter-btn");

const step1Form = document.getElementById("step1Form");
const step2Form = document.getElementById("step2Form");
const sendCodeForm = document.getElementById("sendCodeForm");
const verifyCodeForm = document.getElementById("verifyCodeForm");
const backToStep1Btn = document.getElementById("backToStep1Btn");

const regNameInput = document.getElementById("regName");
const regPhoneInput = document.getElementById("regPhone");
const regTelegramIdInput = document.getElementById("regTelegramId");
const otpCodeInput = document.getElementById("otpCodeInput");

const step1Error = document.getElementById("step1Error");
const step2Error = document.getElementById("step2Error");
const step2Success = document.getElementById("step2Success");
const botLinkBtn = document.getElementById("botLinkBtn");

const navUserName = document.getElementById("navUserName");
const logoutBtn = document.getElementById("logoutBtn");
const toast = document.getElementById("toast");

let activeCategory = "all";
let currentPendingAuth = null;

// ==========================================
// 1. BOT USERNAME ANIQLASH (BACKEND ORQALI)
// ==========================================
async function initBotInfo() {
    try {
        const res = await fetch(`${API_BASE}/api/bot-info`);
        if (res.ok) {
            const data = await res.json();
            if (data.username) {
                botLinkBtn.href = `https://t.me/${data.username}`;
                botLinkBtn.textContent = `✈️ @${data.username} ga kirish (/start)`;
            }
        }
    } catch (e) {
        console.warn("Backend bilan bog'lanishda xatolik (python bot.py ishga tushirilganligini tekshiring):", e);
    }
}

// ==========================================
// 2. MASHINALAR KATALOGINI CHIZISH
// ==========================================
function renderCars() {
    const query = searchInput.value.toLowerCase().trim();
    const filtered = CARS.filter(car => {
        const matchCat = activeCategory === "all" || car.category === activeCategory;
        const matchSearch = car.name.toLowerCase().includes(query) || car.tag.toLowerCase().includes(query);
        return matchCat && matchSearch;
    });

    if (filtered.length === 0) {
        carsGrid.innerHTML = `<p style="color:#94a3b8; grid-column: 1/-1; text-align:center; padding: 30px;">Qidiruv bo'yicha mashina topilmadi.</p>`;
        return;
    }

    carsGrid.innerHTML = filtered.map(car => `
        <div class="car-card">
            <div class="car-img-wrap">
                <img src="${car.img}" alt="${car.name}">
                <span class="car-tag">${car.tag}</span>
            </div>
            <div class="car-body">
                <div class="car-title">${car.name}</div>
                <div class="car-specs">
                    <span class="spec-pill">📅 ${car.year}</span>
                    <span class="spec-pill">🛣️ ${car.km}</span>
                    <span class="spec-pill">⛽ ${car.fuel}</span>
                    <span class="spec-pill">⚙️ ${car.gear}</span>
                </div>
                <div class="car-footer">
                    <div class="car-price">${car.price}</div>
                    <button class="btn btn-primary btn-sm" onclick="handleBuyCar(${car.id})">
                        🛒 Xarid qilish
                    </button>
                </div>
            </div>
        </div>
    `).join("");
}

filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
        filterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeCategory = btn.dataset.category;
        renderCars();
    });
});

searchInput.addEventListener("input", renderCars);

// ==========================================
// 3. FOYDALANUVCHI HOLATI VA XAVFSIZ SESSIYA TEKSHIRUVI
// ==========================================
function getSavedUser() {
    try {
        const user = JSON.parse(localStorage.getItem("autouz_user") || "null");
        if (user && user.name && user.phone && user.session_token) {
            return user;
        }
        return null;
    } catch {
        return null;
    }
}

async function verifySessionWithBackend() {
    const user = getSavedUser();
    if (!user) {
        updateAuthUI(null);
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/check-session`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_token: user.session_token })
        });
        const data = await res.json();
        if (res.ok && data.ok && data.user) {
            updateAuthUI(user);
        } else {
            // Soxta yoki muddati o'tgan sessiya bo'lsa darhol chiqarib yuboramiz!
            localStorage.removeItem("autouz_user");
            updateAuthUI(null);
        }
    } catch (_) {
        // Agar server o'chiq bo'lsa ham ro'yxatdan o'tish ekraniga qaytaramiz
        updateAuthUI(null);
    }
}

function updateAuthUI(verifiedUser) {
    if (verifiedUser) {
        authScreen.classList.add("hidden");
        mainSite.classList.remove("hidden");
        navUserName.textContent = verifiedUser.name;
    } else {
        mainSite.classList.add("hidden");
        authScreen.classList.remove("hidden");
        step2Form.classList.add("hidden");
        step1Form.classList.remove("hidden");
    }
}

logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("autouz_user");
    updateAuthUI(null);
    showToast("Tizimdan chiqdingiz. Qayta kirish uchun ro'yxatdan o'ting.");
});

backToStep1Btn.addEventListener("click", () => {
    step2Form.classList.add("hidden");
    step1Form.classList.remove("hidden");
    step2Error.classList.add("hidden");
});

// ==========================================
// 4. TELEGRAM BOTGA KOD YUBORISH VA TASDIQLASH
// ==========================================
sendCodeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    step1Error.classList.add("hidden");

    const name = regNameInput.value.trim();
    const phone = regPhoneInput.value.trim();
    const telegram_id = regTelegramIdInput.value.trim();
    const sendBtn = document.getElementById("sendCodeBtn");

    sendBtn.disabled = true;
    sendBtn.textContent = "⏳ Yuborilmoqda...";

    try {
        const res = await fetch(`${API_BASE}/api/send-code`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone, telegram_id })
        });
        const data = await res.json();

        if (!res.ok || !data.ok) {
            step1Error.textContent = data.message || "Xatolik yuz berdi!";
            step1Error.classList.remove("hidden");
            sendBtn.disabled = false;
            sendBtn.textContent = "🔑 Telegram botga kod yuborish";
            return;
        }

        currentPendingAuth = { name, phone, telegram_id };
    } catch (_) {
        step1Error.textContent = "Backend server ishlamayapti! Terminalda «python bot.py» buyrug'ini ishga tushiring.";
        step1Error.classList.remove("hidden");
        sendBtn.disabled = false;
        sendBtn.textContent = "🔑 Telegram botga kod yuborish";
        return;
    }

    sendBtn.disabled = false;
    sendBtn.textContent = "🔑 Telegram botga kod yuborish";

    step1Form.classList.add("hidden");
    step2Form.classList.remove("hidden");
    step2Success.textContent = "✅ 6 xonali kod Telegram botga yuborildi!";
    step2Success.classList.remove("hidden");
    otpCodeInput.value = "";
    otpCodeInput.focus();
});

verifyCodeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    step2Error.classList.add("hidden");
    step2Success.classList.add("hidden");

    const code = otpCodeInput.value.trim();
    const verifyBtn = document.getElementById("verifyCodeBtn");

    if (!currentPendingAuth) return;

    verifyBtn.disabled = true;
    verifyBtn.textContent = "⏳ Tekshirilmoqda...";

    try {
        const res = await fetch(`${API_BASE}/api/verify-code`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                phone: currentPendingAuth.phone,
                code: code
            })
        });
        const data = await res.json();

        if (!res.ok || !data.ok) {
            step2Error.textContent = data.message || "Kod noto'g'ri!";
            step2Error.classList.remove("hidden");
            verifyBtn.disabled = false;
            verifyBtn.textContent = "✅ Tasdiqlash va Saytga kirish";
            return;
        }

        localStorage.setItem("autouz_user", JSON.stringify(data.user));
        verifyBtn.disabled = false;
        verifyBtn.textContent = "✅ Tasdiqlash va Saytga kirish";

        step2Form.classList.add("hidden");
        step1Form.classList.remove("hidden");

        updateAuthUI(data.user);
        showToast("🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!");
    } catch (err) {
        step2Error.textContent = "Server bilan aloqa uzildi.";
        step2Error.classList.remove("hidden");
        verifyBtn.disabled = false;
        verifyBtn.textContent = "✅ Tasdiqlash va Saytga kirish";
    }
});

// ==========================================
// 5. MASHINA BUYURTMA QILISH
// ==========================================
window.handleBuyCar = async function (carId) {
    const user = getSavedUser();
    if (!user) {
        showToast("⚠️ Xarid qilish uchun avval ro'yxatdan o'ting!");
        updateAuthUI(null);
        return;
    }

    const car = CARS.find(c => c.id === carId);
    if (!car) return;

    try {
        const res = await fetch(`${API_BASE}/api/order`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_token: user.session_token,
                car_name: car.name,
                car_price: car.price
            })
        });
        if (!res.ok) {
            localStorage.removeItem("autouz_user");
            updateAuthUI(null);
            showToast("⚠️ Sessiyangiz muddati tugagan. Qayta kiring.");
            return;
        }
        showToast(`✅ "${car.name}" uchun arizangiz Telegram botga yuborildi!`);
    } catch (_) {
        showToast("⚠️ Server bilan aloqa yo'q!");
    }
};

function showToast(msg) {
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}

// Dastlabki ishga tushirish
renderCars();
initBotInfo();
verifySessionWithBackend();
