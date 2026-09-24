import { apiFetch } from "./client";

export function getProgress() {
  return apiFetch("/progress");
}
