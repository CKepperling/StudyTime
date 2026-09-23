import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createNote, deleteNote, listNotesForDocument, updateNote } from "../api/notes";

export default function Notes() {
  const { documentId } = useParams();

  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [newContent, setNewContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState(null);

  // Which note (by id) is currently being edited inline - null means
  // "not editing anything", not "editing note id null".
  const [editingId, setEditingId] = useState(null);
  const [editingContent, setEditingContent] = useState("");

  useEffect(() => {
    refreshNotes();
  }, [documentId]);

  function refreshNotes() {
    setLoading(true);
    listNotesForDocument(documentId)
      .then((data) => {
        setNotes(data);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (!newContent.trim()) return;

    setSaving(true);
    setActionError(null);
    try {
      const note = await createNote(documentId, newContent.trim());
      // Prepend rather than refetch the whole list - one less round
      // trip, and the new note appears at the top immediately.
      setNotes((current) => [note, ...current]);
      setNewContent("");
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function startEditing(note) {
    setEditingId(note.id);
    setEditingContent(note.content);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingContent("");
  }

  async function handleSaveEdit(noteId) {
    if (!editingContent.trim()) return;

    setActionError(null);
    try {
      const updated = await updateNote(noteId, editingContent.trim());
      setNotes((current) => current.map((n) => (n.id === noteId ? updated : n)));
      cancelEditing();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleDelete(noteId) {
    setActionError(null);
    try {
      await deleteNote(noteId);
      setNotes((current) => current.filter((n) => n.id !== noteId));
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div>
      <Link to="/" style={backLinkStyle}>
        ← Back to documents
      </Link>
      <h1>Notes</h1>

      <form onSubmit={handleCreate} style={{ marginBottom: 24 }}>
        <textarea
          value={newContent}
          onChange={(event) => setNewContent(event.target.value)}
          placeholder="Add a quick note…"
          rows={3}
          style={textareaStyle}
        />
        <button
          type="submit"
          disabled={!newContent.trim() || saving}
          style={buttonStyle}
        >
          {saving ? "Saving…" : "Add note"}
        </button>
      </form>

      {actionError && (
        <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>{actionError}</p>
      )}

      {loading && <p>Loading notes…</p>}
      {loadError && <p style={{ color: "#9c3b2c" }}>{loadError}</p>}

      {!loading && !loadError && notes.length === 0 && (
        <p>No notes for this document yet.</p>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {notes.map((note) => (
          <div key={note.id} style={noteCardStyle}>
            {editingId === note.id ? (
              <>
                <textarea
                  value={editingContent}
                  onChange={(event) => setEditingContent(event.target.value)}
                  rows={3}
                  style={textareaStyle}
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => handleSaveEdit(note.id)}
                    disabled={!editingContent.trim()}
                    style={buttonStyle}
                  >
                    Save
                  </button>
                  <button onClick={cancelEditing} style={secondaryButtonStyle}>
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <p style={{ margin: "0 0 8px", whiteSpace: "pre-wrap" }}>{note.content}</p>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "#9a9a94" }}>
                    {new Date(note.updated_at).toLocaleString()}
                  </span>
                  <div style={{ display: "flex", gap: 12 }}>
                    <button onClick={() => startEditing(note)} style={linkButtonStyle}>
                      Edit
                    </button>
                    <button onClick={() => handleDelete(note.id)} style={linkButtonStyle}>
                      Delete
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
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

const textareaStyle = {
  width: "100%",
  padding: 10,
  fontSize: 14,
  fontFamily: "inherit",
  border: "1px solid var(--border)",
  borderRadius: 6,
  marginBottom: 8,
  boxSizing: "border-box",
  resize: "vertical",
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

const secondaryButtonStyle = {
  padding: "8px 14px",
  fontSize: 14,
  fontWeight: 600,
  border: "1px solid var(--border)",
  borderRadius: 6,
  background: "transparent",
  cursor: "pointer",
};

const linkButtonStyle = {
  border: "none",
  background: "none",
  color: "var(--accent)",
  fontSize: 13,
  cursor: "pointer",
  padding: 0,
};

const noteCardStyle = {
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 14,
};