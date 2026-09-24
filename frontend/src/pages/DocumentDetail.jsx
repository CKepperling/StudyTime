import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  generateSummaries,
  getDocument,
  listSummariesForDocument,
  listPracticeTestsForDocument,
  generatePracticeTest,
} from "../api/documents";

const LEVEL_LABELS = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

const LEVEL_ORDER = ["easy", "medium", "hard"];

export default function DocumentDetail() {
  const { documentId } = useParams();

  const [document, setDocument] = useState(null);
  const [summaries, setSummaries] = useState([]);
  const [practiceTests, setPracticeTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);

  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);
  const [generateMessage, setGenerateMessage] = useState(null);

  const [generatingTest, setGeneratingTest] = useState(false);
  const [generateTestError, setGenerateTestError] = useState(null);
  const [generateTestMessage, setGenerateTestMessage] = useState(null);

  const [activeLevel, setActiveLevel] = useState("medium");

  useEffect(() => {
    Promise.all([
      getDocument(documentId),
      listSummariesForDocument(documentId),
      listPracticeTestsForDocument(documentId),
    ])
      .then(([doc, docSummaries, docPracticeTests]) => {
        setDocument(doc);
        setSummaries(docSummaries);
        setPracticeTests(docPracticeTests);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, [documentId, refreshCount]);

  async function handleGenerateSummaries() {
    setGenerating(true);
    setGenerateError(null);
    setGenerateMessage(null);

    try {
      await generateSummaries(documentId);
      setGenerateMessage(
        "Generation started — this can take a few seconds. Refreshing…"
      );
      // Same stand-in as the flashcards page: generation runs in the
      // background worker, so a short delay then a refetch is the
      // simplest way to show the result without real-time updates.
      setTimeout(() => setRefreshCount((count) => count + 1), 4000);
    } catch (err) {
      setGenerateError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  const summaryForActiveLevel = summaries.find(
    (summary) => summary.difficulty_level === activeLevel
  );

  async function handleGenerateTest() {
    setGeneratingTest(true);
    setGenerateTestError(null);
    setGenerateTestMessage(null);

    try {
      await generatePracticeTest(documentId);
      setGenerateTestMessage(
        "Generation started — this can take a few seconds. Refreshing…"
      );
      setTimeout(() => setRefreshCount((count) => count + 1), 4000);
    } catch (err) {
      setGenerateTestError(err.message);
    } finally {
      setGeneratingTest(false);
    }
  }

  // In practice zero or one - regenerating replaces the existing test
  // rather than adding another, per the backend's own comment.
  const practiceTest = practiceTests[0];

  return (
    <div>
      <Link to="/" style={backLinkStyle}>
        ← Back to documents
      </Link>

      {loading && <p>Loading document…</p>}
      {loadError && <p style={{ color: "#9c3b2c" }}>{loadError}</p>}

      {document && (
        <>
          <h1 style={{ marginBottom: 4 }}>{document.filename}</h1>
          <p style={{ fontSize: 14, color: "var(--muted, #888)", marginBottom: 20 }}>
            Status: <strong>{document.status}</strong> · Uploaded{" "}
            {new Date(document.created_at).toLocaleString()}
          </p>

          <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
            <Link to={`/documents/${documentId}/flashcards`} style={linkButtonStyle}>
              View flashcards
            </Link>
            <Link to={`/documents/${documentId}/notes`} style={linkButtonStyle}>
              Notes
            </Link>
          </div>

          <div style={{ marginBottom: 12 }}>
            <h2 style={{ fontSize: 18, marginBottom: 12 }}>Summaries</h2>

            {document.status !== "extracted" && (
              <p style={{ fontSize: 14, color: "var(--muted, #888)" }}>
                Summaries can be generated once text extraction finishes
                (current status: {document.status}).
              </p>
            )}

            {document.status === "extracted" && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <button
                    onClick={handleGenerateSummaries}
                    disabled={generating}
                    style={buttonStyle}
                  >
                    {generating
                      ? "Starting…"
                      : summaries.length > 0
                        ? "Regenerate summaries"
                        : "Generate summaries"}
                  </button>
                  {generateMessage && (
                    <span style={{ fontSize: 14, color: "var(--accent)" }}>
                      {generateMessage}
                    </span>
                  )}
                </div>
                {generateError && (
                  <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>
                    {generateError}
                  </p>
                )}

                {summaries.length === 0 && (
                  <p>No summaries yet — generate one above.</p>
                )}

                {summaries.length > 0 && (
                  <>
                    <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                      {LEVEL_ORDER.filter((level) =>
                        summaries.some((s) => s.difficulty_level === level)
                      ).map((level) => (
                        <button
                          key={level}
                          onClick={() => setActiveLevel(level)}
                          style={
                            activeLevel === level ? tabButtonActiveStyle : tabButtonStyle
                          }
                        >
                          {LEVEL_LABELS[level] ?? level}
                        </button>
                      ))}
                    </div>
                    {summaryForActiveLevel && (
                      <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
                        {summaryForActiveLevel.content}
                      </p>
                    )}
                  </>
                )}
              </>
            )}
          </div>

          <div style={{ marginTop: 32 }}>
            <h2 style={{ fontSize: 18, marginBottom: 12 }}>Practice Test</h2>

            {document.status !== "extracted" && (
              <p style={{ fontSize: 14, color: "var(--muted, #888)" }}>
                A practice test can be generated once text extraction finishes
                (current status: {document.status}).
              </p>
            )}

            {document.status === "extracted" && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <button
                    onClick={handleGenerateTest}
                    disabled={generatingTest}
                    style={buttonStyle}
                  >
                    {generatingTest
                      ? "Starting…"
                      : practiceTest
                        ? "Regenerate test"
                        : "Generate practice test"}
                  </button>
                  {generateTestMessage && (
                    <span style={{ fontSize: 14, color: "var(--accent)" }}>
                      {generateTestMessage}
                    </span>
                  )}
                </div>
                {generateTestError && (
                  <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>
                    {generateTestError}
                  </p>
                )}

                {!practiceTest && <p>No practice test yet — generate one above.</p>}

                {practiceTest && (
                  <p>
                    {practiceTest.question_count} question
                    {practiceTest.question_count === 1 ? "" : "s"} ready.{" "}
                    <Link to={`/practice-tests/${practiceTest.id}`} style={{ color: "var(--accent)" }}>
                      Take the test →
                    </Link>
                  </p>
                )}
              </>
            )}
          </div>
        </>
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

const linkButtonStyle = {
  ...buttonStyle,
  display: "inline-block",
  textDecoration: "none",
};

const tabButtonStyle = {
  padding: "6px 12px",
  fontSize: 13,
  fontWeight: 600,
  border: "1px solid var(--border)",
  borderRadius: 6,
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
};

const tabButtonActiveStyle = {
  ...tabButtonStyle,
  background: "var(--accent)",
  color: "#fff",
  border: "1px solid var(--accent)",
};