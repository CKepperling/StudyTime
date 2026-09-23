import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext.jsx";
import DocumentDetail from "./pages/DocumentDetail";
import FlashcardList from "./pages/FlashcardList";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Notes from "./pages/Notes";
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
            <Route path="/documents/:documentId" element={<DocumentDetail />} />
            <Route path="/documents/:documentId/flashcards" element={<FlashcardList />} />
            <Route path="/documents/:documentId/notes" element={<Notes />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}