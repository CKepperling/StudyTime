import { apiFetch } from "./client";

export function listDueFlashcards() {
  return apiFetch("/flashcards/due");
}

export function listFlashcardsForDocument(documentId) {
  return apiFetch(`/documents/${documentId}/flashcards`);
}

export function reviewFlashcard(flashcardId, grade) {
  return apiFetch(`/flashcards/${flashcardId}/review`, {
    method: "POST",
    body: JSON.stringify({ grade }),
  });
}

export function generateFlashcards(documentId) {
  return apiFetch(`/documents/${documentId}/generate-flashcards`, {
    method: "POST",
  });
}

export function createFlashcard(documentId, { front, back }) {
  return apiFetch(`/documents/${documentId}/flashcards`, {
    method: "POST",
    body: JSON.stringify({ front, back }),
  });
}
