import { useEffect, useState } from "react";
import { listDueFlashcards, reviewFlashcard } from "../api/flashcards";

// Matches the grade scale the backend's SM-2 implementation expects
// (0=Again, 1=Hard, 2=Good, 3=Easy) - see backend/app/services/sm2.py.
const GRADES = [
  { value: 0, label: "Again", style: gradeButtonStyle("#9c3b2c") },
  { value: 1, label: "Hard", style: gradeButtonStyle("#a0752c") },
  { value: 2, label: "Good", style: gradeButtonStyle("#3b7a3b") },
  { value: 3, label: "Easy", style: gradeButtonStyle("#2c6e9c") },
];

export default function Review() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [revealed, setRevealed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Inlined directly in the effect (rather than calling out to a
  // named helper) - there's only ever one place this queue gets
  // loaded from, since a review just trims the local array instead
  // of re-fetching.
  useEffect(() => {
    listDueFlashcards()
      .then((cards) => {
        setQueue(cards);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const currentCard = queue[0];

  async function handleGrade(grade) {
    if (!currentCard || submitting) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      await reviewFlashcard(currentCard.id, grade);
      // Drop the just-reviewed card and move on - no need to refetch
      // the whole queue, since a passing grade won't make it due
      // again today and a failing one just goes to the back mentally
      // (the backend reschedules it for tomorrow either way).
      setQueue((previous) => previous.slice(1));
      setRevealed(false);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p>Loading review queue…</p>;

  if (loadError) {
    return <p style={{ color: "#9c3b2c" }}>{loadError}</p>;
  }

  if (!currentCard) {
    return (
      <div>
        <h1>Review queue</h1>
        <p>You're all caught up — no flashcards are due right now.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Review queue</h1>
      <p style={{ color: "#6a6a63", fontSize: 14, marginBottom: 20 }}>
        {queue.length} card{queue.length === 1 ? "" : "s"} due
      </p>

      <div style={cardStyle}>
        <div style={{ fontSize: 13, color: "#6a6a63", marginBottom: 12 }}>
          Question
        </div>
        <div style={{ fontSize: 18, marginBottom: 24 }}>{currentCard.front}</div>

        {revealed ? (
          <>
            <div style={{ fontSize: 13, color: "#6a6a63", marginBottom: 12 }}>
              Answer
            </div>
            <div style={{ fontSize: 18 }}>{currentCard.back}</div>
          </>
        ) : (
          <button onClick={() => setRevealed(true)} style={revealButtonStyle}>
            Show answer
          </button>
        )}
      </div>

      {submitError && (
        <p style={{ color: "#9c3b2c", fontSize: 14, marginTop: 16 }}>
          {submitError}
        </p>
      )}

      {revealed && (
        <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
          {GRADES.map((grade) => (
            <button
              key={grade.value}
              onClick={() => handleGrade(grade.value)}
              disabled={submitting}
              style={grade.style}
            >
              {grade.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const cardStyle = {
  border: "1px solid #d8d8d3",
  borderRadius: 12,
  padding: "32px 28px",
  maxWidth: 480,
};

const revealButtonStyle = {
  padding: "8px 14px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  borderRadius: 6,
  background: "var(--accent)",
  color: "#fff",
  cursor: "pointer",
};

function gradeButtonStyle(color) {
  return {
    flex: 1,
    padding: "10px 0",
    fontSize: 14,
    fontWeight: 600,
    border: "none",
    borderRadius: 6,
    background: color,
    color: "#fff",
    cursor: "pointer",
  };
}
