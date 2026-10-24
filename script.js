// Backend manzillari (Lokal va Render serveri)
const LOCAL_API = "http://127.0.0.1:5000";
const RENDER_API = "https://mashina-savdo.onrender.com";

function getCandidateApis() {
    const list = [];
    if (window.location.protocol.startsWith("http") && !window.location.port.includes("5500")) {
        list.push(window.location.origin);
    }
    list.push(LOCAL_API);
    list.push(RENDER_API);
    return [...new Set(list)];
}

// Zaxira (Fallback) Telegram ulanishi
const _tgKey = ["7047214330", "AAGsqjCpLixZA80jMgBXIlCts2xVmcrMR1A"].join(":");
const TG_API = `https://api.telegram.org/bot${_tgKey}`;

// Boshlang'ich mashinalar ro'yxati
const DEFAULT_CARS = [
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

const registerForm = document.getElementById("registerForm");
const regNameInput = document.getElementById("regName");
const regPhoneInput = document.getElementById("regPhone");
const regError = document.getElementById("regError");

const navUserName = document.getElementById("navUserName");
const adminRoleBadge = document.getElementById("adminRoleBadge");
const logoutBtn = document.getElementById("logoutBtn");
const toast = document.getElementById("toast");

// Admin Modal elementlari
const openAdminBtn = document.getElementById("openAdminBtn");
const heroAdminBtn = document.getElementById("heroAdminBtn");
const adminModal = document.getElementById("adminModal");
const closeAdminModalBtn = document.getElementById("closeAdminModalBtn");
const addCarForm = document.getElementById("addCarForm");

let activeCategory = "all";
let activeBackendUrl = null;
let serverCustomCars = [];

// ==========================================
// ADMIN HUQUQINI TEKSHIRISH
// ==========================================
function isAdminUser() {
    const user = getSavedUser();
    if (!user) return false;
    const lowerName = (user.name || "").toLowerCase();
    // Husniddin yoki Admin ismi bilan kirgan bo'lsa (yoki parol tergan bo'lsa) -> Avtomatik Admin!
    if (lowerName.includes("husniddin") || lowerName.includes("admin")) {
        return true;
    }
    return localStorage.getItem("autouz_is_admin") === "true";
}

function getLocalCustomCars() {
    try {
        return JSON.parse(localStorage.getItem("autouz_custom_cars") || "[]");
    } catch {
        return [];
    }
}

function getDeletedCarIds() {
    try {
        return JSON.parse(localStorage.getItem("autouz_deleted_cars") || "[]");
    } catch {
        return [];
    }
}

function getAllCars() {
    const deletedIds = new Set(getDeletedCarIds().map(String));
    const localCustom = getLocalCustomCars();

    // Server va lokal qo'shilgan mashinalarni birlashtiramiz (dublikatlarsiz)
    const map = new Map();
    for (const c of [...localCustom, ...serverCustomCars, ...DEFAULT_CARS]) {
        const cid = String(c.id);
        if (!deletedIds.has(cid) && !map.has(cid)) {
            map.set(cid, c);
        }
    }
    return Array.from(map.values());
}

// ==========================================
// YORDAMCHI: MAVJUD BACKEND SERVERNI TOPISH
// ==========================================
async function fetchFromBackend(path, options = {}) {
    const candidates = activeBackendUrl ? [activeBackendUrl, ...getCandidateApis()] : getCandidateApis();
    for (const base of [...new Set(candidates)]) {
        try {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 5000);
            const res = await fetch(`${base}${path}`, { ...options, signal: controller.signal });
            clearTimeout(timer);
            const contentType = res.headers.get("content-type") || "";
            if (!contentType.includes("application/json")) {
                continue;
            }
            activeBackendUrl = base;
            return res;
        } catch (_) {}
    }
    throw new Error("BACKEND_UNREACHABLE");
}

async function loadCarsFromServer() {
    try {
        const res = await fetchFromBackend("/api/cars");
        if (res.ok) {
            const data = await res.json();
            if (data.ok && Array.isArray(data.cars)) {
                serverCustomCars = data.cars;
                renderCars();
            }
        }
    } catch (_) {}
}

async function sendTelegramDirectMessage(htmlText) {
    const chatIds = new Set(JSON.parse(localStorage.getItem("autouz_chat_ids") || "[]"));

    try {
        const upRes = await fetch(`${TG_API}/getUpdates`);
        const upData = await upRes.json();
        if (upData.ok && Array.isArray(upData.result)) {
            upData.result.forEach(item => {
                if (item.message && item.message.chat && item.message.chat.id) {
                    chatIds.add(String(item.message.chat.id));
                }
            });
            localStorage.setItem("autouz_chat_ids", JSON.stringify(Array.from(chatIds)));
        }
    } catch (_) {}

    for (const cid of chatIds) {
        try {
            await fetch(`${TG_API}/sendMessage`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chat_id: cid,
                    text: htmlText,
                    parse_mode: "HTML"
                })
            });
        } catch (_) {}
    }
}

// ==========================================
// 1. MASHINALAR KATALOGINI CHIZISH
// ==========================================
function renderCars() {
    const query = searchInput.value.toLowerCase().trim();
    const allCars = getAllCars();
    const isAdmin = isAdminUser();

    const filtered = allCars.filter(car => {
        const matchCat = activeCategory === "all" || car.category === activeCategory;
        const matchSearch = car.name.toLowerCase().includes(query) || (car.tag || "").toLowerCase().includes(query);
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
                    <div style="display:flex; gap:8px;">
                        ${isAdmin ? `<button class="btn btn-danger-outline btn-sm" title="O'chirish" onclick="handleDeleteCar('${car.id}')">🗑️</button>` : ""}
                        <button class="btn btn-primary btn-sm" onclick="handleBuyCar('${car.id}')">
                            🛒 Xarid qilish
                        </button>
                    </div>
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
// 2. FOYDALANUVCHI HOLATI (AUTH GUARD)
// ==========================================
function getSavedUser() {
    try {
        const user = JSON.parse(localStorage.getItem("autouz_user") || "null");
        if (user && user.name && user.phone) {
            return user;
        }
        return null;
    } catch {
        return null;
    }
}

function updateAuthUI() {
    const user = getSavedUser();
    if (user) {
        authScreen.classList.add("hidden");
        mainSite.classList.remove("hidden");
        navUserName.textContent = user.name;

        if (isAdminUser()) {
            adminRoleBadge.classList.remove("hidden");
        } else {
            adminRoleBadge.classList.add("hidden");
        }
        renderCars();
    } else {
        mainSite.classList.add("hidden");
        authScreen.classList.remove("hidden");
        adminModal.classList.add("hidden");
    }
}

logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("autouz_user");
    localStorage.removeItem("autouz_is_admin");
    updateAuthUI();
    showToast("Tizimdan chiqdingiz. Qayta kirish uchun ro'yxatdan o'ting.");
});

// ==========================================
// 3. ISM VA TELEFON ORQALI RO'YXATDAN O'TISH
// ==========================================
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    regError.classList.add("hidden");

    const name = regNameInput.value.trim();
    const phone = regPhoneInput.value.trim();
    const registerBtn = document.getElementById("registerBtn");

    if (!name || phone.length < 7) {
        regError.textContent = "Iltimos, ismingiz va telefon raqamingizni to'liq kiriting!";
        regError.classList.remove("hidden");
        return;
    }

    registerBtn.disabled = true;
    registerBtn.textContent = "⏳ Kirilmoqda...";

    const tokenArray = new Uint8Array(32);
    window.crypto.getRandomValues(tokenArray);
    const localToken = Array.from(tokenArray, b => b.toString(16).padStart(2, "0")).join("");

    let userObj = {
        name: name,
        phone: phone,
        session_token: localToken
    };

    // Agar Husniddin yoki Admin deb kirsa avtomatik admin qilamiz
    if (name.toLowerCase().includes("husniddin") || name.toLowerCase().includes("admin")) {
        localStorage.setItem("autouz_is_admin", "true");
    }

    try {
        const res = await fetchFromBackend("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone })
        });
        const data = await res.json();
        if (res.ok && data.ok && data.user) {
            userObj = data.user;
        }
    } catch (_) {
        sendTelegramDirectMessage(
            `✅ <b>Saytdan yangi odam ro'yxatdan o'tdi!</b>\n\n` +
            `👤 <b>Ism:</b> ${name}\n` +
            `📞 <b>Telefon:</b> ${phone}`
        );
    }

    localStorage.setItem("autouz_user", JSON.stringify(userObj));
    registerBtn.disabled = false;
    registerBtn.textContent = "✅ Ro'yxatdan o'tish va Kirish";

    updateAuthUI();
    showToast(`🎉 Xush kelibsiz, ${name}!`);
});

// ==========================================
// 4. ADMIN PANEL: YANGI MASHINA QO'SHISH VA O'CHIRISH
// ==========================================
function openAdminPanel() {
    if (!isAdminUser()) {
        const pin = prompt("👑 Admin bo'limiga kirish uchun parolni kiriting (Parol: 7777 yoki husniddin):");
        if (!pin) return;
        if (pin.trim().toLowerCase() === "7777" || pin.trim().toLowerCase() === "husniddin" || pin.trim().toLowerCase() === "admin") {
            localStorage.setItem("autouz_is_admin", "true");
            updateAuthUI();
            showToast("👑 Sizga Admin huquqi berildi!");
        } else {
            showToast("❌ Admin paroli noto'g'ri!");
            return;
        }
    }
    adminModal.classList.remove("hidden");
}

openAdminBtn.addEventListener("click", openAdminPanel);
if (heroAdminBtn) {
    heroAdminBtn.addEventListener("click", openAdminPanel);
}

closeAdminModalBtn.addEventListener("click", () => {
    adminModal.classList.add("hidden");
});

adminModal.addEventListener("click", (e) => {
    if (e.target === adminModal) {
        adminModal.classList.add("hidden");
    }
});

function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

addCarForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const saveBtn = document.getElementById("saveCarBtn");
    saveBtn.disabled = true;
    saveBtn.textContent = "⏳ Qo'shilmoqda...";

    const name = document.getElementById("carName").value.trim();
    let price = document.getElementById("carPrice").value.trim();
    if (price && !price.startsWith("$") && !price.toLowerCase().includes("so'm")) {
        price = "$" + price;
    }
    const category = document.getElementById("carCategory").value;
    const tag = document.getElementById("carTag").value.trim() || "Yangi";
    const year = document.getElementById("carYear").value.trim() || "2025";
    const km = document.getElementById("carKm").value.trim() || "0 km";
    const fuel = document.getElementById("carFuel").value.trim() || "Benzin";
    const gear = document.getElementById("carGear").value || "Avtomat";

    const fileInput = document.getElementById("carImgFile");
    const urlInput = document.getElementById("carImgUrl").value.trim();

    let imgData = urlInput || "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=80";
    if (fileInput.files && fileInput.files[0]) {
        try {
            imgData = await readFileAsDataUrl(fileInput.files[0]);
        } catch (_) {}
    }

    const newCar = {
        id: Date.now(),
        name,
        price,
        category,
        tag,
        year,
        km,
        fuel,
        gear,
        img: imgData
    };

    // 1. Lokal xotiraga darhol saqlaymiz
    const customList = getLocalCustomCars();
    customList.unshift(newCar);
    localStorage.setItem("autouz_custom_cars", JSON.stringify(customList));

    // 2. Backend (Neon DB + Telegram Bot) ga ham yuboramiz
    try {
        await fetchFromBackend("/api/cars/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newCar)
        });
    } catch (_) {
        sendTelegramDirectMessage(
            `🚗 <b>ADMIN YANGI MASHINA QO'SHDI!</b>\n\n` +
            `🚘 <b>Model:</b> ${newCar.name}\n` +
            `💰 <b>Narxi:</b> ${newCar.price}\n` +
            `📅 <b>Yili:</b> ${newCar.year} | ${newCar.fuel}`
        );
    }

    saveBtn.disabled = false;
    saveBtn.textContent = "➕ Mashinani katalogga qo'shish";

    addCarForm.reset();
    adminModal.classList.add("hidden");
    renderCars();
    showToast(`✅ "${name}" katalogga muvaffaqiyatli qo'shildi!`);
});

window.handleDeleteCar = async function (carId) {
    if (!isAdminUser()) return;
    if (!confirm("Haqiqatan ham ushbu mashinani katalogdan o'chirmoqchimisiz?")) return;

    // Lokal ro'yxatdan o'chiramiz
    const customList = getLocalCustomCars().filter(c => String(c.id) !== String(carId));
    localStorage.setItem("autouz_custom_cars", JSON.stringify(customList));

    const deletedIds = getDeletedCarIds();
    deletedIds.push(String(carId));
    localStorage.setItem("autouz_deleted_cars", JSON.stringify(deletedIds));

    try {
        await fetchFromBackend("/api/cars/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: carId })
        });
    } catch (_) {}

    renderCars();
    showToast("🗑️ Mashina katalogdan o'chirildi.");
};

// ==========================================
// 5. MASHINA BUYURTMA QILISH
// ==========================================
window.handleBuyCar = async function (carId) {
    const user = getSavedUser();
    if (!user) {
        showToast("⚠️ Xarid qilish uchun avval ro'yxatdan o'ting!");
        updateAuthUI();
        return;
    }

    const car = getAllCars().find(c => String(c.id) === String(carId));
    if (!car) return;

    try {
        const res = await fetchFromBackend("/api/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_token: user.session_token,
                car_name: car.name,
                car_price: car.price
            })
        });
        if (res.ok) {
            showToast(`✅ "${car.name}" uchun arizangiz Telegram botga yuborildi!`);
            return;
        }
    } catch (_) {}

    sendTelegramDirectMessage(
        `🚘 <b>YANGI MASHINA BUYURTMASI!</b>\n\n` +
        `🚗 <b>Model:</b> ${car.name}\n` +
        `💰 <b>Narxi:</b> ${car.price}\n` +
        `👤 <b>Xaridor:</b> ${user.name}\n` +
        `📞 <b>Telefon:</b> ${user.phone}`
    );
    showToast(`✅ "${car.name}" uchun arizangiz Telegram botga yuborildi!`);
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
updateAuthUI();
loadCarsFromServer();
