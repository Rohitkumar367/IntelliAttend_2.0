import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import MonthlyAttendanceChart from "../components/MonthlyAttendanceChart";

export default function ReportsPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [monthCount, setMonthCount] = useState(now.getMonth() + 1);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    if (monthCount < 1 || monthCount > 24) {
      toast.error("Months to include must be between 1 and 24.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.monthlySummary(year, monthCount);
      setItems(res.items || []);
    } catch (error) {
      toast.error(`Failed to load report: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="space-y-5">
      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <h3 className="text-lg font-semibold text-slate-900">Attendance Report</h3>
        <p className="mt-1 text-sm text-slate-600">
          Aggregates attendance from current month backward for the number of months you enter.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
            placeholder="Academic year"
          />
          <input
            type="number"
            min="1"
            max="24"
            value={monthCount}
            onChange={(e) => setMonthCount(Number(e.target.value))}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring"
            placeholder="Months to include"
          />
          <button
            onClick={load}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load Report"}
          </button>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-xl shadow-slate-200/70">
        <MonthlyAttendanceChart items={items} />
      </div>
    </section>
  );
}
