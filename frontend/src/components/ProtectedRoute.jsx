import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/useAuth";

// Wraps a route element and only renders it once we know the visitor
// is signed in. Redirects to /login otherwise, remembering the page
// they were headed to so login can send them back after.
export default function ProtectedRoute({ children }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return <p>Loading…</p>;
  }

  if (status === "signed-out") {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
