import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listFlashcardsForDocument } from "../api/flashcards";

export default function FlashcardList() {
  const { documentId } = useParams();

  const [flashcards, setFlashcards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    listFlashcardsForDocument(documentId)
      .then((cards) => {
        setFlashcards(cards);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, [documentId]);

  return (
    <div>
      <Link to="/" style={backLinkStyle}>
        ← Back to documents
      </Link>
      <h1>Flashcards</h1>

      {loading && <p>Loading flashcards…</p>}
      {loadError && <p style={{ color: "#9c3b2c" }}>{loadError}</p>}

      {!loading && !loadError && flashcards.length === 0 && (
        <p>No flashcards for this document yet.</p>
      )}

      {flashcards.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
              <th style={thStyle}>Front</th>
              <th style={thStyle}>Back</th>
              <th style={thStyle}>Next review</th>
            </tr>
          </thead>
          <tbody>
            {flashcards.map((card) => (
              <tr key={card.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={tdStyle}>{card.front}</td>
                <td style={tdStyle}>{card.back}</td>
                <td style={tdStyle}>{new Date(card.due_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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

const thStyle = { padding: "8px 4px", fontSize: 13, fontWeight: 600 };
const tdStyle = { padding: "8px 4px", fontSize: 14 };
