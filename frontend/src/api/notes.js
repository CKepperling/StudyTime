import { apiFetch } from "./client";

export function listNotesForDocument(documentId) {
  return apiFetch(`/documents/${documentId}/notes`);
}

export function createNote(documentId, content) {
  return apiFetch(`/documents/${documentId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function updateNote(noteId, content) {
  return apiFetch(`/notes/${noteId}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export function deleteNote(noteId) {
  return apiFetch(`/notes/${noteId}`, { method: "DELETE" });
}