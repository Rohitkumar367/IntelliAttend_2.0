import { create } from "zustand";
import { api } from "../api/client";

export const useAppStore = create((set, get) => ({
  // Keep a normalized training status shape for all consumers.
  students: [],
  trainingInfo: {
    status: "idle",
    stage: "idle",
    message: "Not started",
    progressPercent: 0,
    requestedEpochs: null,
    requestedBatchSize: null,
    datasetSize: null,
    metrics: null,
  },
  semesterRows: [],
  lastAttendanceResult: null,

  fetchStudents: async () => {
    const data = await api.listStudents();
    set({ students: data || [] });
    return data || [];
  },

  addStudent: async ({ name, roll_no, images }) => {
    const created = await api.createStudent({ name, roll_no, images });
    await get().fetchStudents();
    return created;
  },

  deleteStudent: async (id) => {
    const result = await api.deleteStudent(id);
    await get().fetchStudents();
    return result;
  },

  deleteStudentByRoll: async (rollNo) => {
    const result = await api.deleteStudentByRoll(rollNo);
    await get().fetchStudents();
    return result;
  },

  startTraining: async (payload) => {
    const res = await api.startTraining(payload);
    set({
      trainingInfo: {
        status: res.status || "unknown",
        stage: res.stage || "unknown",
        message: res.message || "No message",
        progressPercent: Number(res.progress_percent ?? 0) || 0,
        requestedEpochs: res.requested_epochs ?? null,
        requestedBatchSize: res.requested_batch_size ?? null,
        datasetSize: res.dataset_size ?? null,
        metrics: res.metrics ?? null,
      },
    });
    return res;
  },

  refreshTrainingStatus: async () => {
    const res = await api.trainingStatus();
    set({
      trainingInfo: {
        status: res.status || "unknown",
        stage: res.stage || "unknown",
        message: res.message || "No message",
        progressPercent: Number(res.progress_percent ?? 0) || 0,
        requestedEpochs: res.requested_epochs ?? null,
        requestedBatchSize: res.requested_batch_size ?? null,
        datasetSize: res.dataset_size ?? null,
        metrics: res.metrics ?? null,
      },
    });
    return res;
  },

  recognizeAttendanceFrame: async (file) => {
    const result = await api.recognizeFrame(file);
    set({ lastAttendanceResult: result });
    return result;
  },

  getAttendanceLockState: async () => {
    const result = await api.attendanceLockState();
    return result;
  },

  loadSemesterReport: async (year, monthsBackCount) => {
    const count = Number(monthsBackCount);
    if (!Number.isFinite(count) || count < 1) {
      throw new Error("Month count must be at least 1");
    }

    const response = await api.monthlySummary(Number(year), Math.floor(count));
    const rows = response.items || [];
    set({ semesterRows: rows });
    return rows;
  },

  resetSemester: async () => {
    const result = await api.resetSemester();
    set({
      students: [],
      lastAttendanceResult: null,
      semesterRows: [],
      trainingInfo: {
        status: "idle",
        stage: "idle",
        message: "Not started",
        progressPercent: 0,
        requestedEpochs: null,
        requestedBatchSize: null,
        datasetSize: null,
        metrics: null,
      },
    });
    return result;
  },
}));
