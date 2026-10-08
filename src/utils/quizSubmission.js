// Keep an uncertain submission across reloads in this tab. Never replace its key
// or answers until its result is confirmed; Start Quiz explicitly opens a new attempt.
export function createQuizSubmissionStore(storage, scope, makeKey = () => globalThis.crypto.randomUUID()) {
  const storageKey = `learnova-quiz-submission:${JSON.stringify(scope)}`;
  const read = () => {
    const value = storage.getItem(storageKey);
    if (!value) return null;
    const record = JSON.parse(value);
    if (typeof record.key !== "string" || !Array.isArray(record.payload?.answers)) {
      throw new Error("The saved quiz submission could not be restored.");
    }
    return record;
  };
  const save = (record) => storage.setItem(storageKey, JSON.stringify(record));
  return {
    read,
    prepare(payload) {
      const previous = read();
      if (previous) return previous;
      const record = { key: makeKey(), payload };
      save(record); // Fail before sending if retry state cannot be saved.
      return record;
    },
    complete(key, result) {
      const record = read();
      if (!record || record.key !== key) throw new Error("The quiz submission changed. Reload to recover its result.");
      save({ ...record, result });
    },
    reject(key) {
      const record = read();
      if (record?.key === key && !record.result) storage.removeItem(storageKey);
    },
    start() {
      const record = read();
      if (record && !record.result) throw new Error("Retry your pending submission before starting another attempt.");
      storage.removeItem(storageKey);
    },
  };
}
