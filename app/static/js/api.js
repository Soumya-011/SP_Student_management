function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

function openModal(id) {
    document.getElementById(id)?.classList.add("open");
}

function closeModal(id) {
    document.getElementById(id)?.classList.remove("open");
}

async function apiFetch(url, options = {}) {
    const config = {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    };
    const response = await fetch(url, config);

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Session expired. Redirecting to login...");
    }

    if (response.status === 204) {
        return null;
    }

    const data = await response.json();
    if (!response.ok) {
        const msg = Array.isArray(data.detail)
            ? data.detail.map((e) => e.msg).join(", ")
            : data.detail || "Operation failed";
        throw new Error(msg);
    }
    return data;
}

async function logoutAdmin() {
    await fetch("/api/v1/auth/logout", { method: "POST" });
    window.location.href = "/login";
}