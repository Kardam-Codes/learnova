/*
 * File: ReportingDashboardPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor reporting dashboard with summary cards and a learner progress table.
 * What it is: A route-level page that uses the live reporting API for organiser analytics and participant progress review.
 */
import { useEffect, useMemo, useState } from "react";
import InstructorNavbar from "../components/InstructorNavbar";
import EmptyState from "../components/EmptyState";
import LoadingBlock from "../components/LoadingBlock";
import StatusBanner from "../components/StatusBanner";
import { buildGeneratedReportingData } from "../data/generatedDemoData";
import { useAuth } from "../context/AuthContext";
import { fetchAdminCourseProgressReportRequest } from "../utils/apiClient";

const MIN_REPORT_ROWS = 320;

function filterRowsByStatus(rows, activeFilter) {
  return activeFilter ? rows.filter((row) => row.status === activeFilter) : rows;
}

function mergeReportingData(response, activeFilter) {
  const generated = buildGeneratedReportingData(MIN_REPORT_ROWS);
  const generatedRows = filterRowsByStatus(generated.rows, activeFilter);
  const liveRows = response.rows ?? [];
  const fillerNeeded = Math.max(MIN_REPORT_ROWS - liveRows.length, 0);
  const mergedRows = [
    ...liveRows,
    ...generatedRows.slice(0, fillerNeeded).map((row, index) => ({
      ...row,
      id: liveRows.length + index + 1,
    })),
  ];

  return {
    summary: [
      { id: "participants", label: "Total Participants", value: mergedRows.length },
      { id: "yet-to-start", label: "Yet to Start", value: mergedRows.filter((row) => row.status === "yet_to_start").length },
      { id: "in-progress", label: "In Progress", value: mergedRows.filter((row) => row.status === "in_progress").length },
      { id: "completed", label: "Completed", value: mergedRows.filter((row) => row.status === "completed").length },
    ],
    rows: mergedRows,
  };
}

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

const REPORT_COLUMNS = [
  { id: "serial", label: "S.No.", render: (row) => row.id },
  { id: "courseName", label: "Course Name", render: (row) => row.courseName },
  { id: "participantName", label: "Participant name", render: (row) => row.participantName },
  { id: "enrolledDate", label: "Enrolled Date", render: (row) => formatDisplayDate(row.enrolledDate) },
  { id: "startDate", label: "Start date", render: (row) => formatDisplayDate(row.startDate) },
  { id: "timeSpent", label: "Time spent", render: (row) => row.timeSpent },
  { id: "completionPercentage", label: "Completion percentage", render: (row) => row.completionPercentage },
  { id: "completedDate", label: "Completed date", render: (row) => formatDisplayDate(row.completedDate) },
  { id: "status", label: "Status", render: (row) => formatStatusLabel(row.status) },
];

export default function ReportingDashboardPage({ theme, toggleTheme }) {
  const { token } = useAuth();
  const generatedFallback = useMemo(() => buildGeneratedReportingData(MIN_REPORT_ROWS), []);
  const [summary, setSummary] = useState(generatedFallback.summary);
  const [rows, setRows] = useState(generatedFallback.rows);
  const [activeFilter, setActiveFilter] = useState("");
  const [loadError, setLoadError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [visibleColumns, setVisibleColumns] = useState(() =>
    REPORT_COLUMNS.reduce((accumulator, column) => ({ ...accumulator, [column.id]: true }), {}),
  );

  useEffect(() => {
    let isMounted = true;

    const loadReport = async () => {
      setIsLoading(true);
      try {
        const response = await fetchAdminCourseProgressReportRequest(token, activeFilter || undefined);
        if (!isMounted) {
          return;
        }

        const merged = mergeReportingData(response, activeFilter);
        setSummary(merged.summary);
        setRows(merged.rows);
        setLoadError("");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        const fallbackRows = filterRowsByStatus(generatedFallback.rows, activeFilter);
        setSummary([
          { id: "participants", label: "Total Participants", value: fallbackRows.length },
          { id: "yet-to-start", label: "Yet to Start", value: fallbackRows.filter((row) => row.status === "yet_to_start").length },
          { id: "in-progress", label: "In Progress", value: fallbackRows.filter((row) => row.status === "in_progress").length },
          { id: "completed", label: "Completed", value: fallbackRows.filter((row) => row.status === "completed").length },
        ]);
        setRows(fallbackRows);
        setLoadError(error.message || "Live report data could not be loaded.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadReport();
    }

    return () => {
      isMounted = false;
    };
  }, [activeFilter, generatedFallback.rows, generatedFallback.summary, token]);

  const totalRowsLabel = useMemo(() => {
    return rows.length === 1 ? "1 row" : `${rows.length} rows`;
  }, [rows]);

  const activeColumns = REPORT_COLUMNS.filter((column) => visibleColumns[column.id]);

  const toggleColumn = (columnId) => {
    setVisibleColumns((current) => {
      const currentlyVisible = Object.values(current).filter(Boolean).length;
      if (current[columnId] && currentlyVisible === 1) {
        return current;
      }
      return {
        ...current,
        [columnId]: !current[columnId],
      };
    });
  };

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar theme={theme} toggleTheme={toggleTheme} />

      <div className="course-page-card instructor-shell">
        <section className="reporting-shell reporting-shell-annotated">
          <div className="reporting-section-row">
            <TableBadge label="Overview" />
          </div>

          <StatusBanner
            tone={loadError ? "error" : "info"}
            message={loadError ? "Live report data could not be loaded. Showing generated demo reporting data." : ""}
            onClose={() => setLoadError("")}
          />

          {isLoading ? (
            <LoadingBlock
              title="Loading reporting insights"
              description="Collecting participants, status counts, and progress rows."
            />
          ) : (
          <>
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

          <div className="reporting-layout-grid">
          <div className="reporting-table-shell reporting-table-shell-annotated">
            <div className="reporting-section-row reporting-section-row-between">
              <TableBadge label="Users" />
              <span className="reporting-row-count">{totalRowsLabel}</span>
            </div>

            {rows.length ? (
            <div className="reporting-table">
              <div
                className="reporting-table-head reporting-table-head-annotated"
                style={{ gridTemplateColumns: `repeat(${activeColumns.length}, minmax(120px, 1fr))` }}
              >
                {activeColumns.map((column) => (
                  <span key={column.id}>{column.label}</span>
                ))}
              </div>

              {rows.map((row) => (
                <div
                  key={`${row.courseName}-${row.participantName}-${row.id}`}
                  className="reporting-table-row reporting-table-row-annotated"
                  style={{ gridTemplateColumns: `repeat(${activeColumns.length}, minmax(120px, 1fr))` }}
                >
                  {activeColumns.map((column) => (
                    <span key={column.id}>{column.render(row)}</span>
                  ))}
                </div>
              ))}
            </div>
            ) : (
              <EmptyState
                title="No matching learners"
                description="Try removing the current filter to view the full course progress report."
              />
            )}
          </div>
          <aside className="reporting-column-panel">
            <div className="reporting-section-row">
              <TableBadge label="Columns" />
            </div>
            <div className="reporting-column-list">
              {REPORT_COLUMNS.map((column) => (
                <label key={column.id} className="reporting-column-toggle">
                  <input
                    type="checkbox"
                    checked={visibleColumns[column.id]}
                    onChange={() => toggleColumn(column.id)}
                  />
                  <span>{column.label}</span>
                </label>
              ))}
            </div>
          </aside>
          </div>
          </>
          )}
        </section>
      </div>
    </main>
  );
}
