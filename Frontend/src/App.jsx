import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import DashboardLayout from "./layout/DashboardLayout";
import StudentsPage from "./pages/StudentsPage";
import TrainingPage from "./pages/TrainingPage";
import AttendancePage from "./pages/AttendancePage";
import MonthlyLookupPage from "./pages/MonthlyLookupPage";
import AdminPage from "./pages/AdminPage";
import { useAppStore } from "./store/useAppStore";

const sections = ["Home", "Monthly Lookup", "Admin"];
const homeTabs = ["Add Student", "Train Model", "Mark Attendance"];

export default function App() {
  const [activeSection, setActiveSection] = useState("Home");
  const [activeHomeTab, setActiveHomeTab] = useState("Add Student");
  const students = useAppStore((state) => state.students);
  const fetchStudents = useAppStore((state) => state.fetchStudents);
  const trainingInfo = useAppStore((state) => state.trainingInfo);
  const refreshTrainingStatus = useAppStore((state) => state.refreshTrainingStatus);

  const isTrainingRunning = String(trainingInfo?.status || "").toLowerCase() === "running";

  useEffect(() => {
    fetchStudents();
    refreshTrainingStatus().catch(() => {});
  }, [fetchStudents, refreshTrainingStatus]);

  useEffect(() => {
    if (!isTrainingRunning) return;
    setActiveSection("Home");
    setActiveHomeTab("Train Model");
  }, [isTrainingRunning]);

  function handleSectionChange(section) {
    if (isTrainingRunning && section !== "Home") {
      toast.error("Training is in progress. Navigation is locked to Train Model.");
      return;
    }
    setActiveSection(section);
  }

  function handleHomeTabChange(tab) {
    if (isTrainingRunning && tab !== "Train Model") {
      toast.error("Training is in progress. Navigation is locked to Train Model.");
      return;
    }
    setActiveHomeTab(tab);
  }

  return (
    <DashboardLayout
      title="Face Attendance Control Panel"
      menu={
        <>
          {sections.map((section) => (
            <button
              key={section}
              className={[
                "rounded-lg px-4 py-2 text-sm font-semibold transition",
                section === activeSection
                  ? "bg-white text-slate-900 shadow-md"
                  : "bg-slate-700 text-slate-100 hover:bg-slate-600",
                isTrainingRunning && section !== "Home" ? "cursor-not-allowed opacity-60" : "",
              ].join(" ")}
              onClick={() => handleSectionChange(section)}
              disabled={isTrainingRunning && section !== "Home"}
            >
              {section}
            </button>
          ))}
        </>
      }
    >

      {activeSection === "Home" && (
        <>
          <nav className="mb-6 flex flex-wrap gap-2">
            {homeTabs.map((tab) => (
              <button
                key={tab}
                className={[
                  "rounded-lg px-4 py-2 text-sm font-medium transition",
                  tab === activeHomeTab
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200",
                  isTrainingRunning && tab !== "Train Model" ? "cursor-not-allowed opacity-60" : "",
                ].join(" ")}
                onClick={() => handleHomeTabChange(tab)}
                disabled={isTrainingRunning && tab !== "Train Model"}
              >
                {tab}
              </button>
            ))}
          </nav>

          {activeHomeTab === "Add Student" && (
            <StudentsPage students={students} />
          )}
          {activeHomeTab === "Train Model" && <TrainingPage />}
          {activeHomeTab === "Mark Attendance" && <AttendancePage />}
        </>
      )}

      {activeSection === "Monthly Lookup" && <MonthlyLookupPage />}
      {activeSection === "Admin" && (
        <AdminPage students={students} />
      )}
    </DashboardLayout>
  );
}
