/*
 * File: ContentSearch.jsx
 * Owner: KARDAM
 * Purpose: Filter the visible course content items on the detail page.
 * What it is: A reusable search field dedicated to the course overview list.
 */
export default function ContentSearch({ value, onChange }) {
  return (
    // Search currently filters by content title only, per the approved plan.
    <label className="content-search">
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search content"
        aria-label="Search course content"
      />
      <span className="search-icon" aria-hidden="true">
        S
      </span>
    </label>
  );
}
