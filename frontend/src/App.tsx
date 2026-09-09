import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import { AuthProvider } from "./auth/AuthContext";
import ErrorBoundary from "./pages/errors/ErrorBoundary";
import BadRequest from "./pages/errors/BadRequest";
import Unauthorized from "./pages/errors/Unauthorized";
import Forbidden from "./pages/errors/Forbidden";
import NotFound from "./pages/errors/NotFound";
import ServerError from "./pages/errors/ServerError";
import ServiceUnavailable from "./pages/errors/ServiceUnavailable";

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/admin" element={<AdminDashboard />} />

            {/* Directly-navigable error routes, useful for support links and
                for the nginx `error_page` directives to redirect to. */}
            <Route path="/errors/400" element={<BadRequest />} />
            <Route path="/errors/401" element={<Unauthorized />} />
            <Route path="/errors/403" element={<Forbidden />} />
            <Route path="/errors/500" element={<ServerError />} />
            <Route path="/errors/503" element={<ServiceUnavailable />} />

            {/* Catch-all: unmatched client-side routes render the 404 page. */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
