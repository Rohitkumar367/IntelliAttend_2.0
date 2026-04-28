const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const RESET_CONFIRM_TOKEN = import.meta.env.VITE_RESET_CONFIRM_TOKEN || "RESET_SEMESTER";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      const payload = await response.json().catch(() => null);
      const detail = payload?.detail;

      if (typeof detail === "string" && detail.trim()) {
        message = detail;
      } else if (Array.isArray(detail) && detail.length) {
        message = detail
          .map((item) => (typeof item?.msg === "string" ? item.msg : String(item)))
          .join("; ");
      } else if (typeof payload?.message === "string" && payload.message.trim()) {
        message = payload.message;
      }
    } else {
      const text = await response.text().catch(() => "");
      if (text && text.trim()) {
        message = text.trim();
      }
    }

    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function jsonHeaders(extra = {}) {
  return { "Content-Type": "application/json", ...extra };
}

export const api = {
  listStudents: () => request("/students"),

  createStudent: ({ name, roll_no, images }) => {
    const form = new FormData();
    form.append("name", name);
    if (roll_no) form.append("roll_no", roll_no);
    (images || []).forEach((file) => form.append("images", file));
    return request("/students", { method: "POST", body: form });
  },

  deleteStudent: (id) => request(`/students/${id}`, { method: "DELETE" }),
  deleteStudentByRoll: (rollNo) =>
    request(`/students/by-roll/${encodeURIComponent(rollNo)}`, { method: "DELETE" }),

  startTraining: (payload) =>
    request("/training/start", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    }),

  trainingStatus: () => request("/training/status"),

  recognizeFrame: (file) => {
    const form = new FormData();
    form.append("image", file);
    return request("/attendance/recognize", { method: "POST", body: form });
  },

  attendanceLockState: () => request("/attendance/lock-state"),

  monthlySummary: (year, month) =>
    request(`/attendance/monthly-summary?year=${year}&month=${month}`),

  markClassDay: (payload) =>
    request("/attendance/class-day", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    }),

  resetSemester: () =>
    request("/admin/reset-semester", {
      method: "DELETE",
      headers: { "x-confirm-token": RESET_CONFIRM_TOKEN },
    }),

  rebuildEmbeddings: () => request("/admin/rebuild-embeddings", { method: "POST" }),
};
