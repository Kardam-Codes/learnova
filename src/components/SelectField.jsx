/*
 * File: SelectField.jsx
 * Owner: KARDAM
 * Purpose: Render a labeled auth dropdown field.
 * What it is: A reusable select control for role selection in login and signup flows.
 */
export default function SelectField({ id, label, value, onChange, options }) {
  return (
    <label className="auth-field" htmlFor={id}>
      <span>{label}</span>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
