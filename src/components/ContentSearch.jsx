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
        <svg viewBox="0 0 24 24" className="inline-icon">
          <circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" strokeWidth="2.4" />
          <path d="M16 16 21 21" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      </span>
    </label>
  );
}
