import { useEffect, useState } from "react";
import { getProgress } from "../api/progress";

export default function Progress() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    getProgress()
      .then((data) => {
        setStats(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 20 }}>Progress</h1>

      {loading && <p>Loading progress…</p>}
      {loadError && <p style={{ color: "#9c3b2c" }}>{loadError}</p>}

      {stats && (
        <>
          <div style={gridStyle}>
            <StatTile label="Documents" value={stats.total_documents} />
            <StatTile label="Flashcards" value={stats.total_flashcards} />
            <StatTile label="Due now" value={stats.flashcards_due_now} />
            <StatTile label="Mastered" value={stats.cards_mastered} />
          </div>

          <div style={gridStyle}>
            <StatTile label="Reviews today" value={stats.reviews_today} />
            <StatTile label="Reviews (7 days)" value={stats.reviews_last_7_days} />
            <StatTile
              label="Accuracy (7 days)"
              value={
                stats.accuracy_last_7_days === null
                  ? "—"
                  : `${stats.accuracy_last_7_days}%`
              }
            />
            <StatTile
              label="Current streak"
              value={`${stats.current_streak_days} ${
                stats.current_streak_days === 1 ? "day" : "days"
              }`}
            />
          </div>

          {stats.total_flashcards === 0 && (
            <p style={{ marginTop: 8, color: "var(--muted, #888)" }}>
              Upload a document and generate some flashcards to start tracking
              your progress.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }) {
  return (
    <div style={tileStyle}>
      <div style={valueStyle}>{value}</div>
      <div style={labelStyle}>{label}</div>
    </div>
  );
}

const gridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
  gap: 16,
  marginBottom: 16,
};

const tileStyle = {
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: "16px 18px",
};

const valueStyle = {
  fontSize: 28,
  fontWeight: 700,
  marginBottom: 4,
};

const labelStyle = {
  fontSize: 13,
  color: "var(--muted, #888)",
};
