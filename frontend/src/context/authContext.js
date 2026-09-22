import { createContext } from "react";

// Split into its own file (rather than living in AuthContext.jsx)
// purely so that file only exports the AuthProvider component -
// React Fast Refresh works reliably only when a file's exports are
// all components.
export const AuthContext = createContext(null);
