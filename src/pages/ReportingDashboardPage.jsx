/*
 * File: ReportingDashboardPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor reporting dashboard with summary cards and a learner progress table.
 * What it is: A route-level page for organiser analytics and participant progress review.
 */
import InstructorNavbar from "../components/InstructorNavbar";
import { reportRows, reportSummary } from "../data/instructorMock";

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

export default function ReportingDashboardPage() {
  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="reporting-shell reporting-shell-annotated">
          <div className="reporting-section-row">
            <TableBadge label="Overview" />
          </div>

          <div className="report-summary-grid report-summary-grid-annotated">
            {reportSummary.map((item) => (
              <article key={item.id} className="report-summary-card report-summary-card-annotated">
                <div className="report-summary-icon-wrap">
                  <SummaryIcon kind={item.id} />
                </div>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </article>
            ))}
          </div>

          <div className="reporting-table-shell reporting-table-shell-annotated">
            <div className="reporting-section-row reporting-section-row-between">
              <TableBadge label="Users" />
              <span className="reporting-grid-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <line x1="3" y1="9" x2="21" y2="9" />
                  <line x1="9" y1="3" x2="9" y2="21" />
                </svg>
              </span>
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

              {reportRows.map((row) => (
                <div key={row.id} className="reporting-table-row reporting-table-row-annotated">
                  <span>{row.id}</span>
                  <span>{row.courseName}</span>
                  <span>{row.participantName}</span>
                  <span>{row.enrolledDate}</span>
                  <span>{row.startDate}</span>
                  <span>{row.timeSpent}</span>
                  <span>{row.completionPercentage}</span>
                  <span>{row.completedDate}</span>
                  <span>{row.status}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
