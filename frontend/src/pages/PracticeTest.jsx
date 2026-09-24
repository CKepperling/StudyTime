import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getPracticeTest, submitPracticeTest } from "../api/practiceTests";

export default function PracticeTest() {
  const { practiceTestId } = useParams();

  const [test, setTest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // Keyed by question_id, so switching between questions doesn't lose
  // what was typed for the others.
  const [answers, setAnswers] = useState({});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    getPracticeTest(practiceTestId)
      .then((data) => {
        setTest(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }, [practiceTestId]);

  function handleAnswerChange(questionId, value) {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);

    // Every question gets an entry even if left blank - the backend
    // treats a missing question_id the same as an empty string
    // (test_submit_treats_missing_answer_as_incorrect_not_an_error),
    // but sending them all explicitly keeps this page's own intent
    // clear rather than relying on that backend leniency.
    const payload = test.questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] ?? "",
    }));

    try {
      const graded = await submitPracticeTest(practiceTestId, payload);
      setResult(graded);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetake() {
    // A practice test is meant to be freely retaken (see the backend
    // comment on submit_practice_test) - clearing local state and
    // showing the questions again is the whole "retake" flow, no
    // refetch needed since the questions themselves haven't changed.
    setAnswers({});
    setResult(null);
    setSubmitError(null);
  }

  if (loading) return <p>Loading practice test…</p>;
  if (loadError) return <p style={{ color: "#9c3b2c" }}>{loadError}</p>;
  if (!test) return null;

  return (
    <div>
      <Link to={`/documents/${test.document_id}`} style={backLinkStyle}>
        ← Back to document
      </Link>
      <h1>Practice Test</h1>

      {result ? (
        <ResultsView result={result} onRetake={handleRetake} documentId={test.document_id} />
      ) : (
        <form onSubmit={handleSubmit}>
          <p style={{ color: "var(--muted, #888)", marginBottom: 20 }}>
            {test.questions.length} question{test.questions.length === 1 ? "" : "s"} ·
            short answer
          </p>

          {test.questions.map((question, index) => (
            <div key={question.id} style={questionCardStyle}>
              <p style={{ fontWeight: 600, marginBottom: 8 }}>
                {index + 1}. {question.question}
              </p>
              <input
                type="text"
                value={answers[question.id] ?? ""}
                onChange={(event) => handleAnswerChange(question.id, event.target.value)}
                placeholder="Your answer…"
                style={inputStyle}
              />
            </div>
          ))}

          {submitError && (
            <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>{submitError}</p>
          )}

          <button type="submit" disabled={submitting} style={buttonStyle}>
            {submitting ? "Grading…" : "Submit test"}
          </button>
        </form>
      )}
    </div>
  );
}

function ResultsView({ result, onRetake, documentId }) {
  const percent = result.total === 0 ? 0 : Math.round((result.score / result.total) * 100);

  return (
    <div>
      <div style={scoreCardStyle}>
        <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>
          {result.score} / {result.total}
        </p>
        <p style={{ margin: "4px 0 0", color: "var(--muted, #888)" }}>{percent}% correct</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
        {result.results.map((r, index) => (
          <div
            key={r.question_id}
            style={{
              ...questionCardStyle,
              borderColor: r.is_correct ? "#2f6b3d" : "#9c3b2c",
            }}
          >
            <p style={{ fontWeight: 600, marginBottom: 6 }}>
              {index + 1}. {r.question}
            </p>
            <p style={{ margin: "0 0 4px", fontSize: 14 }}>
              Your answer: {r.submitted_answer || <em>(left blank)</em>}
            </p>
            {!r.is_correct && (
              <p style={{ margin: 0, fontSize: 14, color: "#2f6b3d" }}>
                Correct answer: {r.correct_answer}
              </p>
            )}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <button onClick={onRetake} style={buttonStyle}>
          Retake test
        </button>
        <Link to={`/documents/${documentId}`} style={secondaryButtonStyle}>
          Back to document
        </Link>
      </div>
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

const questionCardStyle = {
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 14,
  marginBottom: 12,
};

const inputStyle = {
  width: "100%",
  padding: 10,
  fontSize: 14,
  fontFamily: "inherit",
  border: "1px solid var(--border)",
  borderRadius: 6,
  boxSizing: "border-box",
};

const buttonStyle = {
  padding: "10px 16px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  borderRadius: 6,
  background: "var(--accent)",
  color: "#fff",
  cursor: "pointer",
};

const secondaryButtonStyle = {
  ...buttonStyle,
  display: "inline-block",
  textDecoration: "none",
  background: "transparent",
  color: "inherit",
  border: "1px solid var(--border)",
};

const scoreCardStyle = {
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  marginBottom: 20,
};