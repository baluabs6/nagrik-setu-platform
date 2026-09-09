import { useEffect, useState } from "react";
import { api, Issue, IssueStats } from "../api/client";
import IssueForm from "./IssueForm";

export default function Home() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [stats, setStats] = useState<IssueStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    refresh();
  }, []);

  function refresh() {
    Promise.all([api.listIssues(), api.stats()])
      .then(([issuesRes, statsRes]) => {
        setIssues(issuesRes.results);
        setStats(statsRes);
      })
      .catch(() => {
        // Network/API failures render inline; the error boundary only
        // catches render-time exceptions, not fetch failures.
        setIssues([]);
      })
      .finally(() => setLoading(false));
  }

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: 20, fontFamily: "'IBM Plex Sans', sans-serif" }}>
      <h1 style={{ fontFamily: "'Newsreader', serif" }}>Nagrik Setu</h1>
      {stats && (
        <p>
          {stats.open} open · {stats.resolved} resolved · {stats.total} total reports
        </p>
      )}

      <h2 style={{ fontFamily: "'Newsreader', serif", fontSize: "1.2rem", marginTop: 32 }}>File a report</h2>
      <IssueForm onCreated={() => refresh()} />

      <h2 style={{ fontFamily: "'Newsreader', serif", fontSize: "1.2rem", marginTop: 32 }}>Recent reports</h2>
      {loading ? (
        <p>Loading reports…</p>
      ) : (
        issues.map((i) => (
          <div key={i.id} style={{ marginBottom: 12 }}>
            <strong>{i.tracking_id}</strong> — {i.locality}
            {i.attachment_url && (
              <div>
                <img
                  src={i.thumbnail_url ?? i.attachment_url}
                  alt=""
                  style={{ maxWidth: 160, marginTop: 6, borderRadius: 4 }}
                  // The Lambda that generates thumbnails runs async after
                  // upload, so a very recent photo may 404 on the
                  // thumbnail URL for a few seconds — fall back to the
                  // full-size image rather than showing a broken image icon.
                  onError={(e) => {
                    if (i.attachment_url && e.currentTarget.src !== i.attachment_url) {
                      e.currentTarget.src = i.attachment_url;
                    }
                  }}
                />
              </div>
            )}
          </div>
        ))
      )}
    </main>
  );
}
