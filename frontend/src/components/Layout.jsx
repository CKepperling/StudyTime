import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 220,
          flexShrink: 0,
          borderRight: "1px solid #d8d8d3",
          padding: "24px 16px",
          boxSizing: "border-box",
        }}
      >
        <div style={{ fontWeight: 700, fontSize: 20, marginBottom: 28 }}>
          StudyTime
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <NavLink to="/" style={navLinkStyle}>
            Documents
          </NavLink>
          <NavLink to="/review" style={navLinkStyle}>
            Review queue
          </NavLink>
        </nav>
      </aside>
      <main style={{ flexGrow: 1, padding: "32px 40px", boxSizing: "border-box" }}>
        <Outlet />
      </main>
    </div>
  );
}

function navLinkStyle({ isActive }) {
  return {
    display: "block",
    padding: "10px 12px",
    borderRadius: 8,
    textDecoration: "none",
    color: isActive ? "#1a1a1a" : "#4a4a45",
    background: isActive ? "#eceae4" : "transparent",
    fontWeight: isActive ? 600 : 400,
    fontSize: 14,
  };
}
