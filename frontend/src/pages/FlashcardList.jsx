import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createFlashcard,
  generateFlashcards,
  listFlashcardsForDocument,
} from "../api/flashcards";

export default function FlashcardList() {
  const { documentId } = useParams();

  const [flashcards, setFlashcards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);

  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);
  const [generateMessage, setGenerateMessage] = useState(null);

  const [manualFront, setManualFront] = useState("");
  const [manualBack, setManualBack] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  useEffect(() => {
    listFlashcardsForDocument(documentId)
      .then((cards) => {
        setFlashcards(cards);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, [documentId, refreshCount]);

  async function handleGenerate() {
    setGenerating(true);
    setGenerateError(null);
    setGenerateMessage(null);

    try {
      await generateFlashcards(documentId);
      setGenerateMessage(
        "Generation started — this can take a few seconds. Refreshing…"
      );
      // Generation runs in the background worker, not this request, so
      // there's nothing to await here - a short delay then a refetch
      // is a simple stand-in for real-time updates until the app has
      // some kind of polling/websocket infrastructure.
      setTimeout(() => setRefreshCount((count) => count + 1), 4000);
    } catch (err) {
      setGenerateError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleCreateManual(event) {
    event.preventDefault();
    if (!manualFront.trim() || !manualBack.trim()) return;

    setCreating(true);
    setCreateError(null);

    try {
      const card = await createFlashcard(documentId, {
        front: manualFront.trim(),
        back: manualBack.trim(),
      });
      setFlashcards((prev) => [...prev, card]);
      setManualFront("");
      setManualBack("");
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <Link to="/" style={backLinkStyle}>
        ← Back to documents
      </Link>
      <h1>Flashcards</h1>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <button onClick={handleGenerate} disabled={generating} style={buttonStyle}>
          {generating ? "Starting…" : "Generate flashcards with AI"}
        </button>
        {generateMessage && (
          <span style={{ fontSize: 14, color: "var(--accent)" }}>{generateMessage}</span>
        )}
      </div>
      {generateError && (
        <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>{generateError}</p>
      )}

      {loading && <p>Loading flashcards…</p>}
      {loadError && <p style={{ color: "#9c3b2c" }}>{loadError}</p>}

      {!loading && !loadError && flashcards.length === 0 && (
        <p>No flashcards for this document yet.</p>
      )}

      {flashcards.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
              <th style={thStyle}>Front</th>
              <th style={thStyle}>Back</th>
              <th style={thStyle}>Source</th>
              <th style={thStyle}>Next review</th>
            </tr>
          </thead>
          <tbody>
            {flashcards.map((card) => (
              <tr key={card.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={tdStyle}>{card.front}</td>
                <td style={tdStyle}>{card.back}</td>
                <td style={tdStyle}>
                  {card.source === "ai_generated" ? "AI" : "Manual"}
                </td>
                <td style={tdStyle}>{new Date(card.due_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 style={{ fontSize: 18, marginBottom: 12 }}>Add a flashcard by hand</h2>
      <form onSubmit={handleCreateManual} style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 480 }}>
        <input
          type="text"
          placeholder="Front (question)"
          value={manualFront}
          onChange={(event) => setManualFront(event.target.value)}
          style={inputStyle}
        />
        <textarea
          placeholder="Back (answer)"
          value={manualBack}
          onChange={(event) => setManualBack(event.target.value)}
          style={{ ...inputStyle, minHeight: 60, resize: "vertical" }}
        />
        <button
          type="submit"
          disabled={creating || !manualFront.trim() || !manualBack.trim()}
          style={{ ...buttonStyle, alignSelf: "flex-start" }}
        >
          {creating ? "Adding…" : "Add flashcard"}
        </button>
        {createError && (
          <p style={{ color: "#9c3b2c", fontSize: 14 }}>{createError}</p>
        )}
      </form>
    </div>
  );
}

const backLinkStyle = {
  display: "inline-block",
  marginBottom: 16,
  fontSize: 14,
  color: "var(--accent)",
  textDecoration: "none",
};

const buttonStyle = {
  padding: "8px 14px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  borderRadius: 6,
  background: "var(--accent)",
  color: "#fff",
  cursor: "pointer",
};

const inputStyle = {
  padding: "8px 10px",
  fontSize: 14,
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "transparent",
  color: "inherit",
};

const thStyle = { padding: "8px 4px", fontSize: 13, fontWeight: 600 };
const tdStyle = { padding: "8px 4px", fontSize: 14 };
