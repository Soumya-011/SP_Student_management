let currentDuesList = [];

async function loadPaymentsDashboard() {
    const billingMonth = document.getElementById("billing-month").value;
    const statusFilter = document.getElementById("dues-status-filter").value;
    const q = document.getElementById("dues-search").value.trim();

    const params = new URLSearchParams({ billing_month: billingMonth });
    if (statusFilter) params.append("payment_status", statusFilter);
    if (q) params.append("q", q);

    try {
        const [dues, receipts] = await Promise.all([
            apiFetch(`/api/v1/payments/dues?${params.toString()}`),
            apiFetch(`/api/v1/payments/?billing_month=${encodeURIComponent(billingMonth)}`),
        ]);
        currentDuesList = dues;
        renderDuesTable();
        renderReceiptsTable(receipts);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function renderDuesTable() {
    const tbody = document.getElementById("dues-tbody");
    if (!currentDuesList.length) {
        tbody.innerHTML = `<tr><td colspan="8" style="color:var(--muted);">No student fee records match this filter.</td></tr>`;
        return;
    }

    tbody.innerHTML = currentDuesList
        .map((d) => {
            const breakdown = d.enrollments
                .map((e) => {
                    const cls = e.is_paid ? "badge-green" : "badge-red";
                    const icon = e.is_paid ? "✓ Paid" : "Unpaid";
                    return `<span class="badge ${cls}">${escapeHtml(e.subject)} (${escapeHtml(e.teacher_name)}): ₹${e.monthly_fee} [${icon}]</span>`;
                })
                .join(" ");

            const statusBadge =
                d.payment_status === "PAID"
                    ? `<span class="badge badge-green">PAID</span>`
                    : d.payment_status === "PARTIAL"
                    ? `<span class="badge badge-yellow">PARTIAL</span>`
                    : `<span class="badge badge-red">UNPAID</span>`;

            const actionBtn =
                d.payment_status === "PAID"
                    ? `<span style="color:var(--muted); font-size:0.85rem;">Completed</span>`
                    : `<button class="btn btn-sm btn-success" onclick="openCollectModal(${d.student_id})">Collect Fee</button>`;

            return `
            <tr>
                <td>
                    <strong>${escapeHtml(d.student_name)}</strong>
                    <br><small style="color:var(--muted);">Guardian: ${escapeHtml(d.guardian_name)} (${escapeHtml(d.guardian_phone)})</small>
                </td>
                <td>${escapeHtml(d.grade)}</td>
                <td>${breakdown}</td>
                <td>₹${d.total_expected_fee}</td>
                <td style="color:var(--success); font-weight:600;">₹${d.total_paid}</td>
                <td style="color:var(--danger); font-weight:600;">₹${d.total_pending}</td>
                <td>${statusBadge}</td>
                <td>${actionBtn}</td>
            </tr>
        `;
        })
        .join("");
}

function renderReceiptsTable(receipts) {
    const tbody = document.getElementById("receipts-tbody");
    if (!receipts.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="color:var(--muted);">No payments recorded for this month yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = receipts
        .map(
            (r) => `
        <tr>
            <td><strong>${escapeHtml(r.receipt_no)}</strong></td>
            <td>${escapeHtml(r.payment_date)}</td>
            <td>${escapeHtml(r.student_name)}</td>
            <td>${escapeHtml(r.subject)} (${escapeHtml(r.teacher_name)})</td>
            <td>${escapeHtml(r.billing_month)}</td>
            <td><strong>₹${r.amount_paid}</strong></td>
            <td><span class="badge badge-gray">${escapeHtml(r.payment_method)}</span></td>
        </tr>
    `
        )
        .join("");
}

function openCollectModal(studentId) {
    const summary = currentDuesList.find((d) => d.student_id === studentId);
    if (!summary) return;

    document.getElementById("pay-student-id").value = summary.student_id;
    document.getElementById("pay-billing-month").value = summary.billing_month;
    document.getElementById("payment-modal-title").textContent = `Collect Fee — ${summary.student_name} (${summary.billing_month})`;

    const listEl = document.getElementById("payable-enrollments-list");
    listEl.innerHTML = summary.enrollments
        .map((e) => {
            if (e.is_paid) {
                return `
                <div style="padding:0.5rem 0.75rem; border:1px solid var(--border); border-radius:6px; margin-bottom:0.4rem; background:#f8fafc; color:var(--muted);">
                    ✓ <strong>${escapeHtml(e.subject)}</strong> (${escapeHtml(e.teacher_name)}) — ₹${e.amount_paid}
                    <span class="badge badge-green">Already Paid (${escapeHtml(e.receipt_no)})</span>
                </div>
            `;
            }
            return `
            <label style="display:flex; justify-content:space-between; align-items:center; padding:0.55rem 0.75rem; border:1px solid var(--border); border-radius:6px; margin-bottom:0.4rem; cursor:pointer;">
                <span>
                    <input type="checkbox" class="pay-item-cb" data-enrollment-id="${e.enrollment_id}" data-fee="${e.monthly_fee}" checked onchange="recalcSelectedPaymentTotal()">
                    <strong>${escapeHtml(e.subject)}</strong> — ${escapeHtml(e.teacher_name)}
                </span>
                <strong>₹${e.monthly_fee}</strong>
            </label>
        `;
        })
        .join("");

    recalcSelectedPaymentTotal();
    openModal("payment-modal");
}

function recalcSelectedPaymentTotal() {
    let total = 0;
    document.querySelectorAll(".pay-item-cb:checked").forEach((cb) => {
        total += parseFloat(cb.dataset.fee || "0");
    });
    document.getElementById("pay-selected-total").textContent = total.toFixed(2);
    document.getElementById("pay-submit-btn").disabled = total <= 0;
}

document.getElementById("payment-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const studentId = parseInt(document.getElementById("pay-student-id").value, 10);
    const billingMonth = document.getElementById("pay-billing-month").value;
    const paymentMethod = document.getElementById("pay-method").value;
    const notes = document.getElementById("pay-notes").value.trim() || null;

    const items = [];
    document.querySelectorAll(".pay-item-cb:checked").forEach((cb) => {
        items.push({
            enrollment_id: parseInt(cb.dataset.enrollmentId, 10),
            amount_paid: parseFloat(cb.dataset.fee),
        });
    });

    if (!items.length) {
        showToast("Select at least one unpaid subject", "error");
        return;
    }

    try {
        const res = await apiFetch("/api/v1/payments/", {
            method: "POST",
            body: JSON.stringify({
                student_id: studentId,
                billing_month: billingMonth,
                payment_method: paymentMethod,
                notes,
                items,
            }),
        });
        showToast(`Payment recorded! Receipt: ${res.receipt_no}`);
        closeModal("payment-modal");
        loadPaymentsDashboard();
    } catch (err) {
        showToast(err.message, "error");
    }
});

document.getElementById("billing-month").addEventListener("change", loadPaymentsDashboard);
document.getElementById("dues-status-filter").addEventListener("change", loadPaymentsDashboard);
document.getElementById("dues-search").addEventListener("input", debounce(loadPaymentsDashboard, 280));

loadPaymentsDashboard();