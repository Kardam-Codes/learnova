/*
 * File: ReportingDashboardPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor reporting dashboard with summary cards and a learner progress table.
 * What it is: A route-level page that uses the live reporting API for organiser analytics and participant progress review.
 */
import { useEffect, useMemo, useState } from "react";
import InstructorNavbar from "../components/InstructorNavbar";
import { reportRows, reportSummary } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import { fetchAdminCourseProgressReportRequest } from "../utils/apiClient";

function SummaryIcon({ kind }) {
  if (kind === "participants") {
    return (
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="6" r="3" />
        <path d="M6 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      </svg>
    );
  }

  if (kind === "yet-to-start") {
    return (
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" />
        <line x1="12" y1="7" x2="12" y2="12" />
      </svg>
    );
  }

  if (kind === "in-progress") {
    return (
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="8" />
        <line x1="12" y1="12" x2="17" y2="12" />
        <line x1="12" y1="12" x2="12" y2="7" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="8" />
      <polyline points="8 12 11 15 17 8" />
    </svg>
  );
}

function TableBadge({ label }) {
  return <span className="reporting-section-chip">{label}</span>;
}

function formatDisplayDate(dateValue) {
  if (!dateValue) {
    return "-";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
  }).format(new Date(dateValue));
}

function formatStatusLabel(status) {
  if (status === "yet_to_start") {
    return "Yet to Start";
  }

  if (status === "in_progress") {
    return "In Progress";
  }

  if (status === "completed") {
    return "Completed";
  }

  return status ?? "-";
}

const summaryToFilterMap = {
  participants: "",
  "yet-to-start": "yet_to_start",
  "in-progress": "in_progress",
  completed: "completed",
};

export default function ReportingDashboardPage() {
  const { token } = useAuth();
  const [summary, setSummary] = useState(reportSummary);
  const [rows, setRows] = useState(reportRows);
  const [activeFilter, setActiveFilter] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let isMounted = true;

    const loadReport = async () => {
      try {
        const response = await fetchAdminCourseProgressReportRequest(token, activeFilter || undefined);
        if (!isMounted) {
          return;
        }

        setSummary(response.summary);
        setRows(response.rows);
        setLoadError("");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSummary(reportSummary);
        setRows(reportRows);
        setLoadError(error.message);
      }
    };

    if (token) {
      loadReport();
    }

    return () => {
      isMounted = false;
    };
  }, [activeFilter, token]);

  const totalRowsLabel = useMemo(() => {
    return rows.length === 1 ? "1 row" : `${rows.length} rows`;
  }, [rows]);

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="reporting-shell reporting-shell-annotated">
          <div className="reporting-section-row">
            <TableBadge label="Overview" />
          </div>

          {loadError ? (
            <p className="content-empty">
              Live report data could not be loaded. Showing fallback report data.
            </p>
          ) : null}

          <div className="report-summary-grid report-summary-grid-annotated">
            {summary.map((item) => {
              const filterValue = summaryToFilterMap[item.id] ?? "";
              const isActive = activeFilter === filterValue;

              return (
                <button
                  key={item.id}
                  type="button"
                  className={`report-summary-card report-summary-card-annotated${
                    isActive ? " is-active" : ""
                  }`}
                  onClick={() => setActiveFilter((current) => (current === filterValue ? "" : filterValue))}
                >
                  <div className="report-summary-icon-wrap">
                    <SummaryIcon kind={item.id} />
                  </div>
                  <strong>{item.value}</strong>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="reporting-table-shell reporting-table-shell-annotated">
            <div className="reporting-section-row reporting-section-row-between">
              <TableBadge label="Users" />
              <span className="content-empty">{totalRowsLabel}</span>
            </div>

            <div className="reporting-table">
              <div className="reporting-table-head reporting-table-head-annotated">
                <span>S.No.</span>
                <span>Course Name</span>
                <span>Participant name</span>
                <span>Enrolled Date</span>
                <span>Start date</span>
                <span>Time spent</span>
                <span>Completion percentage</span>
                <span>Completed date</span>
                <span>Status</span>
              </div>

              {rows.map((row) => (
                <div key={`${row.courseName}-${row.participantName}-${row.id}`} className="reporting-table-row reporting-table-row-annotated">
                  <span>{row.id}</span>
                  <span>{row.courseName}</span>
                  <span>{row.participantName}</span>
                  <span>{formatDisplayDate(row.enrolledDate)}</span>
                  <span>{formatDisplayDate(row.startDate)}</span>
                  <span>{row.timeSpent}</span>
                  <span>{row.completionPercentage}</span>
                  <span>{formatDisplayDate(row.completedDate)}</span>
                  <span>{formatStatusLabel(row.status)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
