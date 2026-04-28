import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import ConfirmDeleteDialog from "../components/ConfirmDeleteDialog";

export default function AdminResetPage({ onReset }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function resetSemester() {
    setBusy(true);
    try {
      await api.resetSemester();
      setStatus("System reset completed.");
      toast.success("Semester reset completed.");
      setOpen(false);
      if (onReset) onReset();
    } catch (error) {
      setStatus(`Reset failed: ${error.message}`);
      toast.error(`Reset failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function rebuildEmbeddings() {
    setBusy(true);
    try {
      const res = await api.rebuildEmbeddings();
      setStatus(`Embeddings rebuilt with ${res.samples || 0} samples.`);
      toast.success("Embeddings rebuilt.");
    } catch (error) {
      setStatus(`Rebuild failed: ${error.message}`);
      toast.error(`Rebuild failed: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
      <h3 className="text-lg font-semibold text-slate-900">Reset for New Semester</h3>
      <p className="mt-1 text-sm text-slate-600">
        This permanently deletes students, attendance logs and linked cloud images.
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          className="rounded-lg bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
          onClick={rebuildEmbeddings}
          disabled={busy}
        >
          Rebuild Embeddings
        </button>
        <button
          className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          onClick={() => setOpen(true)}
          disabled={busy}
        >
          Delete Everything
        </button>
      </div>

      {status ? <p className="mt-3 text-sm text-slate-700">{status}</p> : null}

      <ConfirmDeleteDialog
        open={open}
        title="Full Semester Reset"
        message="This action cannot be undone. Continue?"
        onConfirm={resetSemester}
        onCancel={() => setOpen(false)}
      />
    </section>
  );
}
