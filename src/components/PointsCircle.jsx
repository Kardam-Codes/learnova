/*
 * File: PointsCircle.jsx
 * Owner: KARDAM
 * Purpose: Visualize learner points and current badge on the profile panel.
 * What it is: A compact progress-ring style summary for points-based gamification.
 */
export default function PointsCircle({ totalPoints, currentBadge }) {
  const maxPoints = 120;
  const percentage = Math.min((totalPoints / maxPoints) * 100, 100);

  return (
    <div
      className="points-circle"
      style={{
        borderColor: "var(--primary)",
      }}
    >
      <div className="points-circle-inner">
        <strong>{totalPoints}</strong>
        <span>Points</span>
        <small>{currentBadge}</small>
        <em>{Math.round(percentage)}% to master track</em>
      </div>
    </div>
  );
}
