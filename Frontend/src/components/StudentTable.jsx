export default function StudentTable({ students, onDelete }) {
  if (!students?.length) {
    return <p className="mt-3 text-sm text-slate-500">No students added yet.</p>;
  }

  return (
    <div className="mt-3 overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
          <th className="px-3 py-2">Name</th>
          <th className="px-3 py-2">Roll No</th>
          <th className="px-3 py-2">Status</th>
          <th className="px-3 py-2">Created</th>
          <th className="px-3 py-2">Action</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {students.map((student) => (
          <tr key={student.id} className="text-slate-700">
            <td className="px-3 py-3 font-medium">{student.name}</td>
            <td className="px-3 py-3">{student.roll_no || "-"}</td>
            <td className="px-3 py-3">
              <span
                className={[
                  "rounded-full px-2 py-1 text-xs font-semibold",
                  student.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600",
                ].join(" ")}
              >
                {student.active ? "Active" : "Inactive"}
              </span>
            </td>
            <td className="px-3 py-3">
              {student.created_at ? new Date(student.created_at).toLocaleDateString() : "-"}
            </td>
            <td className="px-3 py-3">
              <button
                className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white"
                onClick={() => onDelete(student)}
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
      </table>
    </div>
  );
}
