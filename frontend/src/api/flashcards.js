import { apiFetch } from "./client";

export function listDueFlashcards() {
  return apiFetch("/flashcards/due");
}

export function reviewFlashcard(flashcardId, grade) {
  return apiFetch(`/flashcards/${flashcardId}/review`, {
    method: "POST",
    body: JSON.stringify({ grade }),
  });
}
