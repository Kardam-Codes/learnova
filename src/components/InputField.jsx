/*
 * File: InputField.jsx
 * Owner: KARDAM
 * Purpose: Render a labeled auth input field.
 * What it is: A small reusable form field for standard text and email inputs.
 */
export default function InputField({ id, label, type = "text", value, onChange, placeholder }) {
  return (
    <label className="auth-field" htmlFor={id}>
      <span>{label}</span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}
