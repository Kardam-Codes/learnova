/*
 * File: ProfilePanel.jsx
 * Owner: KARDAM
 * Purpose: Surface learner points and badge progress on the My Courses page only.
 * What it is: A sidebar profile summary composed of the points ring and badge ladder.
 */
import PointsCircle from "./PointsCircle";
import BadgeList from "./BadgeList";

export default function ProfilePanel({ profile }) {
  return (
    <aside className="profile-panel">
      <div className="profile-panel-header">
        <span className="eyebrow">My Profile</span>
        <h2>{profile.learnerName}</h2>
      </div>

      <PointsCircle
        totalPoints={profile.totalPoints}
        currentBadge={profile.currentBadge}
      />

      <div className="profile-current-badge">
        <span className="eyebrow">Current Badge</span>
        <strong>{profile.currentBadge}</strong>
      </div>

      <BadgeList tiers={profile.badgeTiers} currentBadge={profile.currentBadge} />
    </aside>
  );
}
