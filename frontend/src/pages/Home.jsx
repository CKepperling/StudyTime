import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDocuments, uploadDocument } from "../api/documents";

export default function Home() {
  const [documents, setDocuments] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  useEffect(() => {
    refreshDocuments();
  }, []);

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

const thStyle = { padding: "8px 4px", fontSize: 13, fontWeight: 600 };
const tdStyle = { padding: "8px 4px", fontSize: 14 };