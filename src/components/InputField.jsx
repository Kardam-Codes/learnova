/*
 * File: InputField.jsx
 * Owner: KARDAM
 * Purpose: Render a labeled auth input field.
 * What it is: A small reusable form field for standard text and email inputs.
 */
export default function InputField({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  onBlur,
  disabled = false,
  helperText = "",
  errorText = "",
}) {
  return (
    <label className="auth-field" htmlFor={id}>
      <span>{label}</span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={Boolean(errorText)}
      />
      {errorText ? <small className="field-error-text">{errorText}</small> : null}
      {!errorText && helperText ? <small className="field-helper-text">{helperText}</small> : null}
    </label>
  );
}
