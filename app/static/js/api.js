const DESKTOP_MEDIA = window.matchMedia("(min-width: 1024px)");

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getInitials(fullName) {
    if (!fullName) return "NA";
    const parts = String(fullName).trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
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

/* ==========================================================================
   Retractable Off-Canvas Drawer Controller (260px <-> 0px)
   ========================================================================== */
function syncSidebarAccessibility() {
    const html = document.documentElement;
    const sidebar = document.getElementById("app-sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle");
    if (!sidebar) return;

    let isOpen;
    if (DESKTOP_MEDIA.matches) {
        isOpen = html.getAttribute("data-sidebar") !== "collapsed";
    } else {
        isOpen = html.getAttribute("data-mobile-sidebar") === "open";
    }

    // Prevent keyboard Tab focus inside hidden 0px drawer
    sidebar.inert = !isOpen;
    sidebar.setAttribute("aria-hidden", String(!isOpen));
    if (toggleBtn) {
        toggleBtn.setAttribute("aria-expanded", String(isOpen));
    }
}

function toggleSidebar() {
    const html = document.documentElement;
    if (DESKTOP_MEDIA.matches) {
        const isCollapsed = html.getAttribute("data-sidebar") === "collapsed";
        const nextState = isCollapsed ? "open" : "collapsed";
        html.setAttribute("data-sidebar", nextState);
        try {
            localStorage.setItem("sidebar_collapsed", String(nextState === "collapsed"));
        } catch (e) {}
    } else {
        const isMobileOpen = html.getAttribute("data-mobile-sidebar") === "open";
        if (isMobileOpen) {
            html.removeAttribute("data-mobile-sidebar");
        } else {
            html.setAttribute("data-mobile-sidebar", "open");
        }
    }
    syncSidebarAccessibility();
}

function closeMobileSidebar() {
    document.documentElement.removeAttribute("data-mobile-sidebar");
    syncSidebarAccessibility();
}

// Initialize drawer transitions, resize sync, and keyboard shortcuts
document.addEventListener("DOMContentLoaded", () => {
    syncSidebarAccessibility();

    // Remove preload transition lock after initial paint
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.documentElement.classList.remove("preload-transitions");
        });
    });

    // Clear mobile backdrop lock automatically if window resizes to desktop
    DESKTOP_MEDIA.addEventListener("change", (e) => {
        if (e.matches) {
            document.documentElement.removeAttribute("data-mobile-sidebar");
        }
        syncSidebarAccessibility();
    });

    // Keyboard shortcuts: Ctrl+B / Cmd+B toggles drawer; Escape closes modals/mobile drawer
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
            e.preventDefault();
            toggleSidebar();
        } else if (e.key === "Escape") {
            closeMobileSidebar();
            document.querySelectorAll(".modal-backdrop.open").forEach((m) => {
                m.classList.remove("open");
            });
        }
    });
});

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