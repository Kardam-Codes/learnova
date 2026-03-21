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

export default function ReportingDashboardPage() {
  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="reporting-shell">
          <div className="reporting-label-row">
            <span className="eyebrow">Overview</span>
          </div>

          <div className="report-summary-grid">
            {reportSummary.map((item) => (
              <article key={item.id} className="report-summary-card">
                <SummaryIcon kind={item.id} />
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </article>
            ))}
          </div>

          <div className="reporting-table-shell">
            <div className="reporting-label-row">
              <span className="eyebrow">Users</span>
            </div>

            <div className="reporting-table">
              <div className="reporting-table-head">
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
                <div key={row.id} className="reporting-table-row">
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
