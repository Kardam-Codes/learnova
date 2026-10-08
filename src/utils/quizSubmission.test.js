import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createQuizSubmissionStore } from "./quizSubmission.js";

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}
const payload = { answers: [{ questionId: "q1", selectedOptionIndexes: [0] }] };
const scope = ["server", "user", "course", "quiz"];

test("lost response and reload retain original key and answers; explicit start creates another attempt", () => {
  const storage = memoryStorage();
  let sequence = 0;
  const store = () => createQuizSubmissionStore(storage, scope, () => `key-${++sequence}`);
  const first = store().prepare(payload);
  // Simulate the backend committing before the connection drops.
  const receipts = new Map([[first.key, { attemptNumber: 1, pointsEarned: 10 }]]);
  assert.throws(() => store().start(), /pending submission/);
  const retry = store().prepare({ answers: [] });
  assert.deepEqual(retry, first);
  store().complete(retry.key, receipts.get(retry.key));
  assert.deepEqual(store().read().result, { attemptNumber: 1, pointsEarned: 10 });
  assert.equal(receipts.size, 1);
  // Confirmed results survive course-refresh failure and route remounts.
  assert.deepEqual(store().prepare(payload).result, receipts.get(first.key));
  store().start();
  const second = store().prepare(payload);
  assert.notEqual(second.key, first.key);
  assert.equal(second.result, undefined);
});

test("retry records are isolated by server, user, course, and quiz", () => {
  const storage = memoryStorage();
  createQuizSubmissionStore(storage, scope, () => "first").prepare(payload);
  for (let index = 0; index < scope.length; index++) {
    const other = [...scope];
    other[index] += "-other";
    assert.equal(createQuizSubmissionStore(storage, other).read(), null);
  }
});

test("definitive rejection clears only its pending record, never a confirmed result", () => {
  const store = createQuizSubmissionStore(memoryStorage(), scope, () => "key");
  store.prepare(payload);
  store.reject("other");
  assert.ok(store.read());
  store.reject("key");
  assert.equal(store.read(), null);
  store.prepare(payload);
  store.complete("key", { attemptNumber: 1 });
  store.reject("key");
  assert.equal(store.read().result.attemptNumber, 1);
});

test("unavailable storage fails before a new submission can be sent", () => {
  const storage = memoryStorage();
  storage.setItem = () => { throw new Error("storage unavailable"); };
  assert.throws(() => createQuizSubmissionStore(storage, scope).prepare(payload), /storage unavailable/);
});

test("API client sends the optional header only when supplied and keeps HTTP error status", async () => {
  // Import the actual Vite client with only its build-time environment lookup substituted.
  const source = (await readFile(new URL("./apiClient.js", import.meta.url), "utf8"))
    .replace("import.meta.env.VITE_API_BASE_URL", '"http://test.local"');
  const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ attemptNumber: 1 }) };
  };
  try {
    await api.submitQuizAttemptRequest("course", "quiz", "token", payload, "stable-key");
    await api.submitQuizAttemptRequest("course", "quiz", "token", payload);
    assert.equal(calls[0].options.headers["Idempotency-Key"], "stable-key");
    assert.equal(calls[1].options.headers["Idempotency-Key"], undefined);
    assert.deepEqual(JSON.parse(calls[0].options.body), payload);
    await api.fetchQuizSubmissionCapabilitiesRequest("token");
    assert.ok(calls[2].url.endsWith("/courses/quiz-submissions/capabilities"));
    globalThis.fetch = async () => ({ ok: false, status: 422, json: async () => ({ detail: "Invalid answers" }) });
    await assert.rejects(api.submitQuizAttemptRequest("course", "quiz", "token", payload, "key"),
      (error) => error.status === 422 && error.message === "Invalid answers");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
