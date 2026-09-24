import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { deleteDocument, listDocuments, uploadDocument } from "../api/documents";

export default function Home() {
  const [documents, setDocuments] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Which document's "…" menu is open, by id - null means none.
  // Only one can be open at a time.
  const [openMenuId, setOpenMenuId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const menuRef = useRef(null);

  useEffect(() => {
    refreshDocuments();
  }, []);

  // Closes an open menu on any click outside it - without this, the
  // menu would only close by picking an option, which feels stuck if
  // someone opens it and then changes their mind.
  useEffect(() => {
    if (openMenuId === null) return;

    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenMenuId(null);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [openMenuId]);

  function refreshDocuments() {
    setLoadingList(true);
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        setListError(null);
      })
      .catch((err) => setListError(err.message))
      .finally(() => setLoadingList(false));
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadError(null);

    try {
      await uploadDocument(selectedFile);
      setSelectedFile(null);
      event.target.reset();
      refreshDocuments();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(doc) {
    setOpenMenuId(null);

    // A native confirm() is enough here given how destructive this is
    // (it cascades every flashcard, note, summary, and practice test
    // generated from this document) - not worth a custom modal for a
    // single yes/no gate.
    const confirmed = window.confirm(
      `Delete "${doc.filename}"? This removes its flashcards, notes, summaries, and practice test too. This can't be undone.`
    );
    if (!confirmed) return;

    setDeletingId(doc.id);
    setDeleteError(null);

    try {
      await deleteDocument(doc.id);
      // Drop it from local state directly rather than refetching the
      // whole list - one less round trip, and it disappears instantly.
      setDocuments((current) => current.filter((d) => d.id !== doc.id));
    } catch (err) {
      setDeleteError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <h1>Documents</h1>

      <form
        onSubmit={handleUpload}
        style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}
      >
        <input
          type="file"
          accept="application/pdf"
          onChange={(event) => setSelectedFile(event.target.files[0] || null)}
        />
        <button type="submit" disabled={!selectedFile || uploading} style={buttonStyle}>
          {uploading ? "Uploading…" : "Upload"}
        </button>
      </form>
      {uploadError && (
        <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>{uploadError}</p>
      )}
      {deleteError && (
        <p style={{ color: "#9c3b2c", fontSize: 14, marginBottom: 16 }}>{deleteError}</p>
      )}

      {loadingList && <p>Loading documents…</p>}
      {listError && <p style={{ color: "#9c3b2c" }}>{listError}</p>}

      {!loadingList && !listError && documents.length === 0 && (
        <p>No documents yet — upload a PDF to get started.</p>
      )}

      {documents.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
              <th style={thStyle}>Filename</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Uploaded</th>
              <th style={thStyle}></th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={tdStyle}>
                  <Link to={`/documents/${doc.id}`}>{doc.filename}</Link>
                </td>
                <td style={tdStyle}>{doc.status}</td>
                <td style={tdStyle}>{new Date(doc.created_at).toLocaleString()}</td>
                <td style={tdStyle}>
                  <Link to={`/documents/${doc.id}/flashcards`}>Flashcards</Link>
                  {" · "}
                  <Link to={`/documents/${doc.id}/notes`}>Notes</Link>
                </td>
                <td style={{ ...tdStyle, position: "relative", textAlign: "right" }}>
                  <button
                    onClick={() => setOpenMenuId(openMenuId === doc.id ? null : doc.id)}
                    disabled={deletingId === doc.id}
                    aria-label="Document options"
                    style={menuButtonStyle}
                  >
                    {deletingId === doc.id ? "…" : "⋯"}
                  </button>

                  {openMenuId === doc.id && (
                    <div ref={menuRef} style={dropdownStyle}>
                      <button onClick={() => handleDelete(doc)} style={dropdownItemStyle}>
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

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

// Header padding increased from the original 8px to give the row
// below it real breathing room - the filename link was sitting almost
// flush against the divider line before this.
const thStyle = { padding: "8px 4px 14px", fontSize: 13, fontWeight: 600 };

// Vertical padding increased from 8px to 14px - this is the actual
// fix for "the title is very close to the text below it": each row
// simply needed more height, not a change to the text itself.
const tdStyle = { padding: "14px 4px", fontSize: 14 };

const menuButtonStyle = {
  width: 28,
  height: 28,
  borderRadius: "50%",
  border: "1px solid var(--border)",
  background: "transparent",
  color: "inherit",
  fontSize: 16,
  lineHeight: 1,
  cursor: "pointer",
};

const dropdownStyle = {
  position: "absolute",
  top: "100%",
  right: 0,
  marginTop: 4,
  background: "var(--bg-elevated, #1a1a1a)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  overflow: "hidden",
  zIndex: 10,
  minWidth: 100,
};

const dropdownItemStyle = {
  display: "block",
  width: "100%",
  padding: "8px 14px",
  fontSize: 14,
  textAlign: "left",
  border: "none",
  background: "transparent",
  color: "#9c3b2c",
  cursor: "pointer",
};