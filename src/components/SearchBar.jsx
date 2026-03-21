/*
 * File: SearchBar.jsx
 * Owner: KARDAM
 * Purpose: Provide course-level search on the My Courses page.
 * What it is: A reusable search input for filtering the visible course catalog.
 */
export default function SearchBar({ value, onChange, placeholder }) {
  return (
    <label className="content-search catalog-search">
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label="Search all courses"
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
