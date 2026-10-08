/*
 * File: BadgeList.jsx
 * Owner: KARDAM
 * Purpose: Show the points-to-badge ladder for the learner profile panel.
 * What it is: A presentational list explaining how badge tiers map to total points.
 */
export default function BadgeList({ tiers, currentBadge }) {
  return (
    <div className="badge-list">
      {tiers.map((tier) => (
        <div
          key={tier.name}
          className={`badge-row ${tier.name === currentBadge ? "is-current" : ""}`}
        >
          <span>{tier.name}</span>
          <span>
            {tier.minPoints}-{tier.maxPoints} Points
          </span>
        </div>
      ))}
    </div>
  );
}
