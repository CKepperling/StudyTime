import { apiFetch } from "./client";

export function listDocuments() {
  return apiFetch("/documents");
}

export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/documents", {
    method: "POST",
    body: formData,
  });
}

export function getDocument(documentId) {
  return apiFetch(`/documents/${documentId}`);
}

export function deleteDocument(documentId) {
  return apiFetch(`/documents/${documentId}`, { method: "DELETE" });
}

export function listSummariesForDocument(documentId) {
  return apiFetch(`/documents/${documentId}/summaries`);
}

export function generateSummaries(documentId) {
  return apiFetch(`/documents/${documentId}/generate-summaries`, {
    method: "POST",
  });
}

export function listPracticeTestsForDocument(documentId) {
  return apiFetch(`/documents/${documentId}/practice-tests`);
}

export function generatePracticeTest(documentId) {
  return apiFetch(`/documents/${documentId}/generate-practice-test`, {
    method: "POST",
  });
}