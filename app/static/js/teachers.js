let allTeachers = [];

async function loadTeachers() {
    const q = document.getElementById("teacher-search").value.trim();
    const url = q ? `/api/v1/teachers/?q=${encodeURIComponent(q)}` : "/api/v1/teachers/";
    try {
        allTeachers = await apiFetch(url);
        renderTeachersTable();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function renderTeachersTable() {
    const tbody = document.getElementById("teachers-tbody");
    if (!allTeachers.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="color:var(--muted);">No teachers found.</td></tr>`;
        return;
    }

    tbody.innerHTML = allTeachers.map((t) => {
        const subjectsHtml = t.subjects
            .map((s) => `<span class="badge badge-blue">${escapeHtml(s)}</span>`)
            .join(" ");

        const scheduleHtml = t.schedules.length
            ? t.schedules
                  .map(
                      (sc) =>
                          `<div style="font-size:0.8rem; margin-bottom:0.2rem;">
                              <strong>${escapeHtml(sc.day_name.slice(0, 3))}</strong>
                              ${sc.start_time.slice(0, 5)}–${sc.end_time.slice(0, 5)}
                              <span class="badge badge-gray">${escapeHtml(sc.subject)} (${escapeHtml(sc.grade_batch)})</span>
                          </div>`
                  )
                  .join("")
            : `<span style="color:var(--muted); font-size:0.8rem;">No slots</span>`;

        return `
            <tr>
                <td><strong>${escapeHtml(t.full_name)}</strong></td>
                <td>${escapeHtml(t.phone)}<br><small style="color:var(--muted);">${escapeHtml(t.email || "")}</small></td>
                <td>${subjectsHtml}</td>
                <td>₹${t.default_monthly_fee}</td>
                <td><span class="badge badge-green">${t.active_students_count} active</span></td>
                <td>${scheduleHtml}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="openEditTeacherModal(${t.id})">Edit</button>
                    <button class="btn btn-sm" onclick="openScheduleModal(${t.id})">Schedule</button>
                </td>
            </tr>
        `;
    }).join("");
}

function openTeacherModal() {
    document.getElementById("teacher-modal-title").textContent = "Add Teacher";
    document.getElementById("teacher-id").value = "";
    document.getElementById("teacher-form").reset();
    document.getElementById("t-fee").value = "500";
    openModal("teacher-modal");
}

function openEditTeacherModal(teacherId) {
    const t = allTeachers.find((item) => item.id === teacherId);
    if (!t) return;
    document.getElementById("teacher-modal-title").textContent = "Edit Teacher";
    document.getElementById("teacher-id").value = t.id;
    document.getElementById("t-name").value = t.full_name;
    document.getElementById("t-phone").value = t.phone;
    document.getElementById("t-email").value = t.email || "";
    document.getElementById("t-fee").value = t.default_monthly_fee;
    document.getElementById("t-subjects").value = t.subjects.join(", ");
    openModal("teacher-modal");
}

document.getElementById("teacher-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("teacher-id").value;
    const subjects = document
        .getElementById("t-subjects")
        .value.split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    const payload = {
        full_name: document.getElementById("t-name").value.trim(),
        phone: document.getElementById("t-phone").value.trim(),
        email: document.getElementById("t-email").value.trim() || null,
        default_monthly_fee: parseFloat(document.getElementById("t-fee").value),
        subjects,
    };

    try {
        if (id) {
            await apiFetch(`/api/v1/teachers/${id}`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
            showToast("Teacher updated");
        } else {
            await apiFetch("/api/v1/teachers/", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            showToast("Teacher added");
        }
        closeModal("teacher-modal");
        loadTeachers();
    } catch (err) {
        showToast(err.message, "error");
    }
});

async function openScheduleModal(teacherId) {
    const teacher = allTeachers.find((t) => t.id === teacherId);
    if (!teacher) return;

    document.getElementById("sched-teacher-id").value = teacher.id;
    document.getElementById("schedule-modal-title").textContent = `Weekly Timetable — ${teacher.full_name}`;

    const subjectSelect = document.getElementById("sched-subject");
    subjectSelect.innerHTML = teacher.subjects
        .map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`)
        .join("");

    await refreshScheduleModalList(teacher.id);
    openModal("schedule-modal");
}

async function refreshScheduleModalList(teacherId) {
    const schedules = await apiFetch(`/api/v1/schedules/teacher/${teacherId}`);
    const container = document.getElementById("schedule-list-container");

    if (!schedules.length) {
        container.innerHTML = `<p style="color:var(--muted); font-size:0.9rem;">No weekly classes scheduled yet.</p>`;
        return;
    }

    container.innerHTML = schedules
        .map(
            (sc) => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.75rem; border:1px solid var(--border); border-radius:6px; margin-bottom:0.4rem;">
                <div>
                    <strong>${escapeHtml(sc.day_name)}</strong>: ${sc.start_time.slice(0, 5)} – ${sc.end_time.slice(0, 5)}
                    | <span class="badge badge-blue">${escapeHtml(sc.subject)}</span>
                    <strong>${escapeHtml(sc.grade_batch)}</strong>
                    ${sc.room ? `<small style="color:var(--muted);">(${escapeHtml(sc.room)})</small>` : ""}
                </div>
                <button class="btn btn-sm btn-danger" onclick="deleteScheduleSlot(${sc.id}, ${teacherId})">Delete</button>
            </div>
        `
        )
        .join("");
}

document.getElementById("schedule-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const teacherId = parseInt(document.getElementById("sched-teacher-id").value, 10);
    const payload = {
        teacher_id: teacherId,
        day_of_week: parseInt(document.getElementById("sched-day").value, 10),
        subject: document.getElementById("sched-subject").value,
        start_time: document.getElementById("sched-start").value,
        end_time: document.getElementById("sched-end").value,
        grade_batch: document.getElementById("sched-batch").value.trim(),
        room: document.getElementById("sched-room").value.trim() || null,
    };

    try {
        await apiFetch("/api/v1/schedules/", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        showToast("Schedule slot added");
        await refreshScheduleModalList(teacherId);
        loadTeachers();
    } catch (err) {
        showToast(err.message, "error");
    }
});

async function deleteScheduleSlot(scheduleId, teacherId) {
    try {
        await apiFetch(`/api/v1/schedules/${scheduleId}`, { method: "DELETE" });
        showToast("Schedule slot removed");
        await refreshScheduleModalList(teacherId);
        loadTeachers();
    } catch (err) {
        showToast(err.message, "error");
    }
}

document.getElementById("teacher-search").addEventListener("input", debounce(loadTeachers, 280));
loadTeachers();