import { useState } from "react";
import toast from "react-hot-toast";
import { useAppStore } from "../store/useAppStore";

export default function MonthlyLookupPage() {
  const rows = useAppStore((state) => state.semesterRows);
  const loadReport = useAppStore((state) => state.loadSemesterReport);
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [monthsBack, setMonthsBack] = useState(now.getMonth() + 1);
  const [loading, setLoading] = useState(false);

  async function loadSemesterReport() {
    if (monthsBack < 1) {
      toast.error("Months to include must be at least 1.");
      return;
    }

    if (monthsBack > 24) {
      toast.error("Months to include cannot exceed 24.");
      return;
    }

    setLoading(true);
    try {
      await loadReport(year, monthsBack);
      toast.success("Semester report loaded.");
    } catch (error) {
      toast.error(`Failed to load report: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h3 className="text-lg font-semibold text-slate-900">Monthly Lookup (Semester Report)</h3>
        <p className="mt-1 text-sm text-slate-600">
          Fetches monthly summaries from the current month backward for the number of months you enter.
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Example: if current month is April and you enter 4, report includes April, March, February, and January.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="grid gap-1 text-xs font-medium text-slate-600">
            Academic Year
            <input
              type="number"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              placeholder="e.g. 2026"
            />
          </label>
          <label className="grid gap-1 text-xs font-medium text-slate-600">
            Months To Include
            <input
              type="number"
              min="1"
              max="24"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
              value={monthsBack}
              onChange={(e) => setMonthsBack(Number(e.target.value))}
              placeholder="e.g. 4"
            />
          </label>
          <div className="flex items-end">
            <button
              type="button"
              onClick={loadSemesterReport}
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {loading ? "Loading..." : "Load Report"}
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h4 className="text-base font-semibold text-slate-900">Semester Table</h4>
        {rows.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No report rows yet.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            {(() => {
              const semesterClassDays = Math.max(
                ...rows.map((row) => Number(row.present_days || 0) + Number(row.absent_days || 0)),
                1
              );

              return (
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Student</th>
                  <th className="px-3 py-2">Present Days</th>
                  <th className="px-3 py-2">Absent Days</th>
                  <th className="px-3 py-2">Semester Class Days</th>
                  <th className="px-3 py-2">Attendance %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => {
                  const presentDays = Number(row.present_days || 0);
                  const absentDays = Math.max(0, Number(row.absent_days || 0));
                  const percentage = ((presentDays / semesterClassDays) * 100).toFixed(1);
                  return (
                    <tr key={row.student_id}>
                      <td className="px-3 py-3 font-medium text-slate-800">{row.student_name}</td>
                      <td className="px-3 py-3 text-emerald-700">{presentDays}</td>
                      <td className="px-3 py-3 text-rose-600">{absentDays}</td>
                      <td className="px-3 py-3 text-slate-700">{semesterClassDays}</td>
                      <td className="px-3 py-3 text-slate-700">{percentage}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
              );
            })()}
          </div>
        )}
      </div>
    </section>
  );
}
