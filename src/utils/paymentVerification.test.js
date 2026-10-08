import test from "node:test";
import assert from "node:assert/strict";
import { createPaymentVerificationStore } from "./paymentVerification.js";

const payload = { razorpayOrderId: "order_test", razorpayPaymentId: "pay_test", razorpaySignature: "synthetic" };
function memory() {
  const values = new Map();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key) };
}

test("uncertain verification survives reload and clears only after confirmation", () => {
  const storage = memory();
  const store = () => createPaymentVerificationStore(storage, ["server", "user", "course"]);
  store().save(payload);
  assert.deepEqual(store().read(), payload);
  store().save(payload);
  assert.throws(() => store().save({ ...payload, razorpayPaymentId: "pay_other" }), /pending payment/);
  assert.deepEqual(store().read(), payload);
  store().clear();
  assert.equal(store().read(), null);
});

test("verification callback is isolated by account, server, and course", () => {
  const storage = memory();
  const scope = ["server", "user", "course"];
  createPaymentVerificationStore(storage, scope).save(payload);
  for (let index = 0; index < scope.length; index++) {
    const other = [...scope];
    other[index] += "-other";
    assert.equal(createPaymentVerificationStore(storage, other).read(), null);
  }
});

test("invalid or unavailable callback storage fails without discarding existing data", () => {
  const storage = memory();
  const store = createPaymentVerificationStore(storage, ["scope"]);
  assert.throws(() => store.save({}), /could not be restored/);
  store.save(payload);
  storage.setItem = () => { throw new Error("unavailable"); };
  assert.throws(() => store.save(payload), /unavailable/);
  assert.deepEqual(store.read(), payload);
});
