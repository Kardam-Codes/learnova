// A successful checkout callback must be verified, not replaced by another checkout
// when confirmation is uncertain. Keep it in this tab until the server confirms access.
export function createPaymentVerificationStore(storage, scope) {
  const key = `learnova-payment-verification:${JSON.stringify(scope)}`;
  const validate = (payload) => {
    if (!["razorpayOrderId", "razorpayPaymentId", "razorpaySignature"].every(
      (field) => typeof payload?.[field] === "string" && payload[field].length > 0,
    )) throw new Error("The payment callback could not be restored.");
    return payload;
  };
  return {
    read() {
      const value = storage.getItem(key);
      return value ? validate(JSON.parse(value)) : null;
    },
    save(payload) {
      validate(payload);
      const previous = this.read();
      if (previous && JSON.stringify(previous) !== JSON.stringify(payload)) {
        throw new Error("Confirm the pending payment before verifying another checkout.");
      }
      storage.setItem(key, JSON.stringify(payload));
    },
    clear() { storage.removeItem(key); },
  };
}
