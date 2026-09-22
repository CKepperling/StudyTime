import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext.jsx";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Review from "./pages/Review";
import Signup from "./pages/Signup";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Everything under here requires a signed-in user - the
              Layout (nav + logout button) only renders once that's
              confirmed, and its child routes render into its Outlet. */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Home />} />
            <Route path="/review" element={<Review />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
