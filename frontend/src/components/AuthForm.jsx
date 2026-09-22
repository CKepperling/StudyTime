// Shared shell for the login and signup forms - same two fields, same
// layout, same error/submitting handling. Only the title, the submit
// label, the password autocomplete hint, and the footer link differ
// between the two pages, so those come in as props instead of two
// near-identical components.
export default function AuthForm({
  title,
  onSubmit,
  email,
  onEmailChange,
  password,
  onPasswordChange,
  error,
  submitting,
  submitLabel,
  passwordAutoComplete,
  footer,
}) {
  return (
    <div style={{ maxWidth: 360, margin: "64px auto", textAlign: "left" }}>
      <h1 style={{ fontSize: 32, marginBottom: 24 }}>{title}</h1>
      <form
        onSubmit={onSubmit}
        style={{ display: "flex", flexDirection: "column", gap: 12 }}
      >
        <label style={labelStyle}>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => onEmailChange(event.target.value)}
            required
            autoComplete="email"
            style={inputStyle}
          />
        </label>
        <label style={labelStyle}>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
            required
            minLength={8}
            autoComplete={passwordAutoComplete}
            style={inputStyle}
          />
        </label>
        {error && (
          <p style={{ color: "#9c3b2c", margin: 0, fontSize: 14 }}>{error}</p>
        )}
        <button type="submit" disabled={submitting} style={buttonStyle}>
          {submitting ? "…" : submitLabel}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: 14 }}>{footer}</p>
    </div>
  );
}

const labelStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
  fontSize: 14,
  fontWeight: 600,
};

const inputStyle = {
  padding: "8px 10px",
  fontSize: 15,
  border: "1px solid var(--border)",
  borderRadius: 6,
  fontFamily: "inherit",
};

const buttonStyle = {
  padding: "10px 12px",
  fontSize: 15,
  fontWeight: 600,
  border: "none",
  borderRadius: 6,
  background: "var(--accent)",
  color: "#fff",
  cursor: "pointer",
};
