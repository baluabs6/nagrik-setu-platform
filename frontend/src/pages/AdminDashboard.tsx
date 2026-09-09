import { useEffect, useState } from "react";
import { api, ApiError, Issue } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Forbidden from "./errors/Forbidden";

const STATUS_OPTIONS: Issue["status"][] = ["submitted", "progress", "resolved"];

export default function AdminDashboard() {
  const { isAuthenticated } = useAuth();
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .listIssues()
      .then((res) => setIssues(res.results))
      .catch(() => setError("Couldn't load reports."))
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  // The backend is the real gatekeeper (IsStaffForStatusChange returns a
  // 403 for non-staff PATCHes) — this client-side check just avoids
  // showing a dashboard that will fail on every action for a signed-in
  // citizen who isn't staff.
  if (!isAuthenticated) {
    return <Forbidden />;
  }

  async function handleStatusChange(issue: Issue, status: Issue["status"]) {
    setUpdatingId(issue.id);
    setError(null);
    try {
      const updated = await api.updateStatus(issue.id, status);
      setIssues((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "Your account doesn't have permission to update report status."
          : "Couldn't update that report. Try again."
      );
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: 20, fontFamily: "'IBM Plex Sans', sans-serif" }}>
      <h1 style={{ fontFamily: "'Newsreader', serif" }}>Ward admin dashboard</h1>
      {error && <p role="alert">{error}</p>}
      {loading ? (
        <p>Loading reports…</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Tracking ID</th>
              <th style={{ textAlign: "left" }}>Locality</th>
              <th style={{ textAlign: "left" }}>Category</th>
              <th style={{ textAlign: "left" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              <tr key={issue.id}>
                <td>{issue.tracking_id}</td>
                <td>{issue.locality}</td>
                <td>{issue.category}</td>
                <td>
                  <select
                    value={issue.status}
                    disabled={updatingId === issue.id}
                    onChange={(e) => handleStatusChange(issue, e.target.value as Issue["status"])}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
