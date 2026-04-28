import { useState } from "react";
import toast from "react-hot-toast";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";
import { useAppStore } from "../store/useAppStore";

const TRAINING_EPOCHS = 8;
const TRAINING_BATCH_SIZE = 8;

export default function AdminPage({ students }) {
  const trainingInfo = useAppStore((state) => state.trainingInfo);
  const startTraining = useAppStore((state) => state.startTraining);
  const refreshTrainingStatus = useAppStore((state) => state.refreshTrainingStatus);
  const resetSemester = useAppStore((state) => state.resetSemester);
  const deleteStudent = useAppStore((state) => state.deleteStudent);
  const deleteStudentByRoll = useAppStore((state) => state.deleteStudentByRoll);
  const [busy, setBusy] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [rollNoToDelete, setRollNoToDelete] = useState("");

  async function handleStartTraining() {
    setBusy(true);
    try {
      const res = await startTraining({ epochs: TRAINING_EPOCHS, batch_size: TRAINING_BATCH_SIZE });
      if (res?.already_running) {
        toast("Training already running.");
      } else {
        toast.success("Training started.");
      }
    } catch (error) {
      toast.error(`Training failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshTraining() {
    setBusy(true);
    try {
      await refreshTrainingStatus();
      toast.success("Training status refreshed.");
    } catch (error) {
      toast.error(`Status failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleResetSemester() {
    setBusy(true);
    try {
      await resetSemester();
      setSelectedStudent(null);
      toast.success("Semester reset complete.");
    } catch (error) {
      toast.error(`Reset failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeleteStudent() {
    if (!selectedStudent) return;
    setBusy(true);
    try {
      await deleteStudent(selectedStudent.id);
      setSelectedStudent(null);
      toast.success("Student deleted.");
    } catch (error) {
      toast.error(`Delete failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteByRoll() {
    const roll = rollNoToDelete.trim();
    if (!roll) {
      toast.error("Please enter a roll number.");
      return;
    }

    setBusy(true);
    try {
      await deleteStudentByRoll(roll);
      setRollNoToDelete("");
      toast.success(`Student with roll no "${roll}" deleted.`);
    } catch (error) {
      toast.error(`Delete by roll failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h3 className="text-lg font-semibold text-slate-900">Admin Actions</h3>
        <p className="mt-1 text-sm text-slate-600">
          Manage critical operations: train model, reset semester, and remove students.
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Training runs with epochs={TRAINING_EPOCHS} and batch size={TRAINING_BATCH_SIZE}.
        </p>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleStartTraining}
            disabled={busy}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Train Model
          </button>
          <button
            type="button"
            onClick={handleRefreshTraining}
            disabled={busy}
            className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
          >
            Refresh Training Status
          </button>
          <button
            type="button"
            onClick={handleResetSemester}
            disabled={busy}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Reset Semester
          </button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-500">Status</p>
            <p className="font-semibold text-slate-900">{trainingInfo.status}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-500">Stage</p>
            <p className="font-semibold text-slate-900">{trainingInfo.stage}</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3">
            <p className="text-xs text-slate-500">Message</p>
            <p className="font-semibold text-slate-900">{trainingInfo.message}</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h4 className="text-base font-semibold text-slate-900">Delete Student by Roll No</h4>
        <p className="mt-1 text-sm text-slate-600">
          Enter roll number and delete student directly from backend endpoint.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <input
            type="text"
            value={rollNoToDelete}
            onChange={(e) => setRollNoToDelete(e.target.value)}
            placeholder="Enter roll number (e.g. 23CS001)"
            className="min-w-60 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
            disabled={busy}
          />
          <button
            type="button"
            onClick={handleDeleteByRoll}
            disabled={busy}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Delete by Roll No
          </button>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h4 className="text-base font-semibold text-slate-900">Delete Student</h4>
        {students?.length ? (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Roll No</th>
                  <th className="px-3 py-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {students.map((student) => (
                  <tr key={student.id}>
                    <td className="px-3 py-3 font-medium text-slate-800">{student.name}</td>
                    <td className="px-3 py-3 text-slate-700">{student.roll_no || "-"}</td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        onClick={() => setSelectedStudent(student)}
                        className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No students available.</p>
        )}
      </div>

      <ConfirmDeleteDialog
        open={Boolean(selectedStudent)}
        title="Delete Student"
        message={
          selectedStudent
            ? `Delete ${selectedStudent.name} and all linked data?`
            : "Delete selected student?"
        }
        onConfirm={confirmDeleteStudent}
        onCancel={() => setSelectedStudent(null)}
      />
    </section>
  );
}
