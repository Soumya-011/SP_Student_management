let studentsList = [];
let activeTeachers = [];

async function initStudentsPage() {
    try {
        activeTeachers = await apiFetch("/api/v1/teachers/?active_only=true");
        const teacherFilter = document.getElementById("filter-teacher");
        teacherFilter.innerHTML =
            `<option value="">All Teachers</option>` +
            activeTeachers
                .map((t) => `<option value="${t.id}">${escapeHtml(t.full_name)} (${escapeHtml(t.subjects.join(", "))})</option>`)
                .join("");

        await loadStudents();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadStudents() {
    const q = document.getElementById("student-search").value.trim();
    const teacherId = document.getElementById("filter-teacher").value;
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (teacherId) params.append("teacher_id", teacherId);

    try {
        studentsList = await apiFetch(`/api/v1/students/?${params.toString()}`);
        renderStudentsTable();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function renderStudentsTable() {
    const tbody = document.getElementById("students-tbody");
    if (!studentsList.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="color:var(--text-muted);">No students found.</td></tr>`;
        return;
    }

    tbody.innerHTML = studentsList
        .map((s) => {
            const activeEnrolls = s.enrollments.filter((e) => e.is_active);
            const badges = activeEnrolls.length
                ? activeEnrolls
                      .map(
                          (e) =>
                              `<span class="badge badge-blue num-tabular">${escapeHtml(e.subject)} · ${escapeHtml(e.teacher_name)} (₹${e.monthly_fee})</span>`
                      )
                      .join(" ")
                : `<span class="badge badge-yellow badge-status">No active teachers</span>`;

            return `
            <tr>
                <td>
                    <div class="identity-cell">
                        <span class="avatar-circle avatar-blue">${escapeHtml(getInitials(s.full_name))}</span>
                        <div class="identity-meta">
                            <span class="identity-name">${escapeHtml(s.full_name)}</span>
                            <span class="identity-sub">${escapeHtml(s.phone || "No personal phone")}</span>
                        </div>
                    </div>
                </td>
                <td><span class="badge badge-gray">${escapeHtml(s.grade)}</span></td>
                <td>
                    <div class="identity-meta">
                        <span class="identity-name" style="font-weight:500;">${escapeHtml(s.guardian_name)}</span>
                        <span class="identity-sub">${escapeHtml(s.guardian_phone)}</span>
                    </div>
                </td>
                <td>${badges}</td>
                <td class="col-num"><strong>₹${s.total_monthly_fee}</strong><small style="color:var(--text-muted);">/mo</small></td>
                <td class="col-num">
                    <button class="btn btn-sm btn-secondary" onclick="openEditStudentModal(${s.id})">Edit</button>
                    <button class="btn btn-sm" onclick="openEnrollmentsModal(${s.id})">Teachers (${activeEnrolls.length})</button>
                </td>
            </tr>
        `;
        })
        .join("");
}

function openNewStudentModal() {
    document.getElementById("student-modal-title").textContent = "Register New Student";
    document.getElementById("student-id").value = "";
    document.getElementById("student-form").reset();
    document.getElementById("initial-enrollments-section").style.display = "block";

    const container = document.getElementById("initial-enrollment-options");
    const options = [];
    activeTeachers.forEach((t) => {
        t.subjects.forEach((sub) => {
            options.push(`
                <div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0.25rem; border-bottom:1px solid var(--border);">
                    <label style="display:flex; align-items:center; gap:0.55rem; cursor:pointer; font-size:0.875rem;">
                        <input type="checkbox" class="init-enroll-cb" data-teacher-id="${t.id}" data-subject="${escapeHtml(sub)}">
                        <span><strong>${escapeHtml(sub)}</strong> — ${escapeHtml(t.full_name)}</span>
                    </label>
                    <input type="number" step="0.01" class="init-enroll-fee num-tabular" value="${t.default_monthly_fee}" style="width:110px; padding:0.28rem 0.5rem;">
                </div>
            `);
        });
    });
    container.innerHTML = options.length
        ? options.join("")
        : `<p style="color:var(--text-muted); font-size:0.85rem;">Add teachers first to select initial enrollments.</p>`;

    openModal("student-modal");
}

function openEditStudentModal(studentId) {
    const s = studentsList.find((item) => item.id === studentId);
    if (!s) return;
    document.getElementById("student-modal-title").textContent = "Edit Student Profile";
    document.getElementById("student-id").value = s.id;
    document.getElementById("s-name").value = s.full_name;
    document.getElementById("s-grade").value = s.grade;
    document.getElementById("s-phone").value = s.phone || "";
    document.getElementById("s-guardian").value = s.guardian_name;
    document.getElementById("s-guardian-phone").value = s.guardian_phone;
    document.getElementById("initial-enrollments-section").style.display = "none";
    openModal("student-modal");
}

document.getElementById("student-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("student-id").value;
    const payload = {
        full_name: document.getElementById("s-name").value.trim(),
        grade: document.getElementById("s-grade").value.trim(),
        phone: document.getElementById("s-phone").value.trim() || null,
        guardian_name: document.getElementById("s-guardian").value.trim(),
        guardian_phone: document.getElementById("s-guardian-phone").value.trim(),
    };

    try {
        if (id) {
            await apiFetch(`/api/v1/students/${id}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
            showToast("Student profile updated");
        } else {
            const enrollments = [];
            document.querySelectorAll(".init-enroll-cb:checked").forEach((cb) => {
                const row = cb.closest("div");
                const feeVal = parseFloat(row.querySelector(".init-enroll-fee").value);
                enrollments.push({
                    teacher_id: parseInt(cb.dataset.teacherId, 10),
                    subject: cb.dataset.subject,
                    monthly_fee: isNaN(feeVal) ? null : feeVal,
                });
            });
            payload.enrollments = enrollments;

            await apiFetch("/api/v1/students/", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            showToast("Student registered");
        }
        closeModal("student-modal");
        loadStudents();
    } catch (err) {
        showToast(err.message, "error");
    }
});

async function openEnrollmentsModal(studentId) {
    const student = await apiFetch(`/api/v1/students/${studentId}`);
    document.getElementById("enroll-student-id").value = student.id;
    document.getElementById("enrollments-modal-title").textContent = `Teachers & Subjects — ${student.full_name}`;

    const listEl = document.getElementById("current-enrollments-list");
    if (!student.enrollments.length) {
        listEl.innerHTML = `<p style="color:var(--text-muted);">Not enrolled with any teachers yet.</p>`;
    } else {
        listEl.innerHTML = student.enrollments
            .map(
                (e) => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.8rem; border:1px solid var(--border); border-radius:var(--radius-sm); margin-bottom:0.45rem; background:var(--bg-canvas);">
                <div>
                    <strong>${escapeHtml(e.subject)}</strong> — ${escapeHtml(e.teacher_name)}
                    <span class="badge badge-status ${e.is_active ? "badge-green" : "badge-red"}">${e.is_active ? "Active" : "Dropped"}</span>
                    <span class="num-tabular" style="font-size:0.84rem; color:var(--text-muted);">₹${e.monthly_fee}/month</span>
                </div>
                <div>
                    <button class="btn btn-sm ${e.is_active ? "btn-danger" : "btn-success"}"
                        onclick="toggleEnrollmentStatus(${student.id}, ${e.id}, ${!e.is_active})">
                        ${e.is_active ? "Drop" : "Reactivate"}
                    </button>
                </div>
            </div>
        `
            )
            .join("");
    }

    const selectEl = document.getElementById("enroll-teacher-subject");
    const opts = [];
    activeTeachers.forEach((t) => {
        t.subjects.forEach((sub) => {
            opts.push(
                `<option value="${t.id}|${escapeHtml(sub)}|${t.default_monthly_fee}">
                    ${escapeHtml(sub)} — ${escapeHtml(t.full_name)} (Default: ₹${t.default_monthly_fee})
                </option>`
            );
        });
    });
    selectEl.innerHTML = opts.join("");
    syncDefaultEnrollmentFee();

    openModal("enrollments-modal");
}

function syncDefaultEnrollmentFee() {
    const selectEl = document.getElementById("enroll-teacher-subject");
    if (!selectEl.value) return;
    const parts = selectEl.value.split("|");
    document.getElementById("enroll-fee").value = parts[2] || "500";
}

document.getElementById("enroll-teacher-subject").addEventListener("change", syncDefaultEnrollmentFee);

document.getElementById("add-enrollment-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const studentId = parseInt(document.getElementById("enroll-student-id").value, 10);
    const [teacherIdStr, subject] = document.getElementById("enroll-teacher-subject").value.split("|");
    const fee = parseFloat(document.getElementById("enroll-fee").value);

    try {
        await apiFetch(`/api/v1/students/${studentId}/enrollments`, {
            method: "POST",
            body: JSON.stringify({
                teacher_id: parseInt(teacherIdStr, 10),
                subject,
                monthly_fee: fee,
            }),
        });
        showToast("Teacher enrollment added");
        await openEnrollmentsModal(studentId);
        loadStudents();
    } catch (err) {
        showToast(err.message, "error");
    }
});

async function toggleEnrollmentStatus(studentId, enrollmentId, makeActive) {
    try {
        await apiFetch(`/api/v1/students/${studentId}/enrollments/${enrollmentId}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: makeActive }),
        });
        showToast(makeActive ? "Enrollment reactivated" : "Enrollment dropped");
        await openEnrollmentsModal(studentId);
        loadStudents();
    } catch (err) {
        showToast(err.message, "error");
    }
}

document.getElementById("student-search").addEventListener("input", debounce(loadStudents, 280));
document.getElementById("filter-teacher").addEventListener("change", loadStudents);
initStudentsPage();