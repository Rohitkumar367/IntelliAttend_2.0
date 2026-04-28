export default function MonthlyAttendanceChart({ items }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-500">No report data available.</p>;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((row) => (
        <div className="rounded-xl border border-slate-200 bg-white p-4" key={row.student_id}>
          <h4 className="font-semibold text-slate-900">{row.student_name}</h4>
          <p className="mt-1 text-sm text-emerald-700">Present Days: {row.present_days}</p>
          <p className="text-sm text-rose-600">Absent Days: {row.absent_days}</p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full bg-blue-600"
              style={{ width: `${Math.min(100, row.present_days * 5)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
