import { apiFetch } from "./client";

// Fetches the test's questions WITHOUT correct answers - matches the
// backend's TestQuestionOut schema, which deliberately leaves
// correct_answer out so it can't be read off the network response
// before submitting.
export function getPracticeTest(practiceTestId) {
  return apiFetch(`/practice-tests/${practiceTestId}`);
}

// answers: [{ question_id, answer }, ...]
export function submitPracticeTest(practiceTestId, answers) {
  return apiFetch(`/practice-tests/${practiceTestId}/submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}