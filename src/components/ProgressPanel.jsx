import ProgressBar from "./ProgressBar";
import StatsCardGroup from "./StatsCardGroup";

export default function ProgressPanel({ progress }) {
  return (
    <aside className="progress-panel">
      {/* Top summary gives learners an at-a-glance completion snapshot. */}
      <div className="progress-header">
        <span className="eyebrow">Course progress</span>
        <strong>{progress.completionPercentage}% Completed</strong>
      </div>
      <ProgressBar percentage={progress.completionPercentage} />
      <StatsCardGroup progress={progress} />
      <p className="progress-note">
        Includes lesson and quiz progress for the enrolled learner.
      </p>
    </aside>
  );
}
