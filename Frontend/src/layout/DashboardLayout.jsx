import { FaUserGraduate } from "react-icons/fa";

export default function DashboardLayout({ title, menu, children }) {
  return (
    <div className="min-h-screen w-full px-3 py-5 sm:px-6 sm:py-7 lg:px-8">
      <header className="mb-8 rounded-2xl bg-slate-900 px-5 py-4 shadow-xl shadow-slate-300/50">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/15 text-white">
              <FaUserGraduate size={20} />
            </span>
            <div>
              <h1 className="text-lg font-bold text-white sm:text-xl">{title}</h1>
              <p className="text-xs text-slate-300 sm:text-sm">
                Add student, run embedding build, and mark attendance from live camera.
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-2">
            {menu}
          </nav>
        </div>
      </header>
      <main className="w-full">{children}</main>
    </div>
  );
}
