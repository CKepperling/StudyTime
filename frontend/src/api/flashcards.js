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
