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
