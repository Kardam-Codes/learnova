/*
 * File: TagBadge.jsx
 * Owner: KARDAM
 * Purpose: Show a compact topic tag on each course card.
 * What it is: A small presentational badge used to surface course categories.
 */
export default function TagBadge({ tag }) {
  return <span className="catalog-tag">{tag}</span>;
}
