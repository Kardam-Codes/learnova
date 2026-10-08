/*
 * File: PaymentFlowPage.jsx
 * Owner: KARDAM
 * Purpose: Run the learner-side paid course checkout flow.
 * What it is: A Razorpay-backed payment page that creates orders, launches checkout, and verifies successful payments.
 */
import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPaymentVerificationStore } from "../utils/paymentVerification";
import Navbar from "../components/Navbar";
import StatusBanner from "../components/StatusBanner";
import LoadingBlock from "../components/LoadingBlock";
import {
  API_BASE_URL,
  createCoursePaymentOrderRequest,
  fetchCourseDetailRequest,
  verifyCoursePaymentRequest,
} from "../utils/apiClient";
import { useAuth } from "../context/AuthContext";

function loadRazorpayCheckout() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve(window.Razorpay);
      return;
    }

    const existingScript = document.querySelector('script[data-razorpay-sdk="true"]');
    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(window.Razorpay), { once: true });
      existingScript.addEventListener("error", () => reject(new Error("Razorpay SDK could not be loaded.")), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.dataset.razorpaySdk = "true";
    script.onload = () => resolve(window.Razorpay);
    script.onerror = () => reject(new Error("Razorpay SDK could not be loaded."));
    document.body.appendChild(script);
  });
}

export default function PaymentFlowPage({ theme, toggleTheme }) {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const [course, setCourse] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pendingPayment, setPendingPayment] = useState(null);
  const pendingRef = useRef(null);
  const busy = useRef(null);
  const verificationStore = useMemo(() => createPaymentVerificationStore({
    getItem: (key) => window.sessionStorage.getItem(key),
    setItem: (key, value) => window.sessionStorage.setItem(key, value),
    removeItem: (key) => window.sessionStorage.removeItem(key),
  }, [API_BASE_URL, user?.id, courseId]), [user?.id, courseId]);
  const activeStore = useRef(verificationStore);
  activeStore.current = verificationStore;

  useEffect(() => {
    busy.current = null;
    setIsProcessing(false);
    pendingRef.current = null;
    setPendingPayment(null);
    try {
      const pending = verificationStore.read();
      pendingRef.current = pending;
      setPendingPayment(pending);
    } catch {
      setError("Saved payment confirmation could not be loaded. Check browser storage before starting checkout.");
    }
  }, [verificationStore]);

  useEffect(() => {
    let isMounted = true;

    const loadCourse = async () => {
      setIsLoading(true);
      try {
        const response = await fetchCourseDetailRequest(courseId, token);
        if (isMounted) {
          setCourse(response);
          setError("");
        }
      } catch (loadError) {
        if (isMounted) {
          setCourse(null);
          setError(loadError.message || "The payment course could not be loaded.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadCourse();
    }

    return () => {
      isMounted = false;
    };
  }, [courseId, token]);

  const confirmPayment = async (payload) => {
    if (activeStore.current !== verificationStore || busy.current === "verification") return;
    if (pendingRef.current && JSON.stringify(pendingRef.current) !== JSON.stringify(payload)) {
      setError("Confirm your pending payment before starting another checkout.");
      return;
    }
    busy.current = "verification";
    pendingRef.current = payload;
    setPendingPayment(payload);
    setIsProcessing(true);
    setError("");
    try {
      // The payment already happened at the provider. If storage is unavailable,
      // still try confirmation and retain the callback in memory for a local retry.
      try { verificationStore.save(payload); } catch {
        setError("Browser storage is unavailable. Keep this page open until payment confirmation succeeds.");
      }
      const updatedCourse = await verifyCoursePaymentRequest(courseId, token, payload);
      if (activeStore.current !== verificationStore) return;
      if (!updatedCourse?.isEnrolled) throw new Error("Payment confirmation did not unlock the course. Please contact support.");
      try { verificationStore.clear(); } catch { /* Replaying a confirmed callback is safe. */ }
      pendingRef.current = null;
      setPendingPayment(null);
      setCourse(updatedCourse);
      setMessage("Payment confirmed. The course is now unlocked for you.");
      navigate(`/courses/${courseId}`);
    } catch (verifyError) {
      if (activeStore.current === verificationStore) {
        setError((verifyError.message || "Payment confirmation could not be completed.") + " Retry confirmation before paying again.");
      }
    } finally {
      if (activeStore.current === verificationStore) {
        busy.current = null;
        setIsProcessing(false);
      }
    }
  };

  const handleCheckout = async () => {
    if (busy.current || pendingRef.current) return;
    // Detect unavailable storage before opening a payable checkout where possible.
    try {
      verificationStore.read();
      const probe = "learnova-payment-storage-check";
      window.sessionStorage.setItem(probe, "1");
      window.sessionStorage.removeItem(probe);
    } catch {
      setError("Browser storage is unavailable. Enable it before starting checkout.");
      return;
    }
    busy.current = "checkout";
    setIsProcessing(true);
    setError("");
    setMessage("");
    let opened = false;

    try {
      const RazorpayCheckout = await loadRazorpayCheckout();
      const order = await createCoursePaymentOrderRequest(courseId, token);
      if (activeStore.current !== verificationStore) return;

      if (order.alreadyPaid) {
        setMessage("This course is already paid and ready to start.");
        navigate(`/courses/${courseId}`);
        return;
      }

      const razorpay = new RazorpayCheckout({
        key: order.keyId,
        amount: order.amount,
        currency: order.currency,
        name: "Learnova",
        description: `Enrollment for ${order.courseTitle}`,
        order_id: order.orderId,
        prefill: {
          name: order.learnerName || user?.name || "",
          email: order.learnerEmail || user?.email || "",
        },
        notes: {
          courseSlug: order.courseSlug,
        },
        theme: {
          color: "#2563EB",
        },
        handler: (response) => confirmPayment({
              razorpayOrderId: response.razorpay_order_id,
              razorpayPaymentId: response.razorpay_payment_id,
              razorpaySignature: response.razorpay_signature,
            }),
        modal: {
          ondismiss: () => {
            if (activeStore.current === verificationStore && busy.current === "checkout") {
              busy.current = null;
              setIsProcessing(false);
            }
          },
        },
      });

      razorpay.open();
      opened = true;
    } catch (checkoutError) {
      if (activeStore.current === verificationStore) setError(checkoutError.message || "Checkout could not be started.");
    } finally {
      if (!opened && activeStore.current === verificationStore) {
        busy.current = null;
        setIsProcessing(false);
      }
    }
  };

  return (
    <main className="course-page-shell">
      <Navbar
        brandName="Learnova"
        learnerName={user?.name ?? "Learner"}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card reviews-shell">
        <StatusBanner tone="success" message={message} onClose={() => setMessage("")} />
        <StatusBanner tone="error" message={error} onClose={() => setError("")} />
        {pendingPayment ? (
          <section>
            <p>Your payment confirmation is pending. Retry it before starting another checkout.</p>
            <button type="button" className="catalog-action-button" disabled={isProcessing}
              onClick={() => confirmPayment(pendingPayment)}>
              {isProcessing ? "Confirming payment..." : "Retry payment confirmation"}
            </button>
          </section>
        ) : null}
        <div className="reviews-header">
          <div>
            <span className="eyebrow">Payment Flow</span>
            <h2>{course?.title ?? courseId}</h2>
          </div>
          <Link className="back-link" to="/my-courses">
            Back to My Courses
          </Link>
        </div>

        {isLoading ? (
          <LoadingBlock
            title="Preparing checkout"
            description="Loading course pricing and payment access information."
          />
        ) : course ? (
          <section className="payment-panel">
            <div className="payment-summary">
              <span className="sticker">Secure checkout</span>
              <h3>Complete enrollment for {course.title}</h3>
              <p>{course.shortDescription}</p>
              <div className="payment-price-row">
                <span>Course fee</span>
                <strong>INR {course.price ?? 0}</strong>
              </div>
              <button
                type="button"
                className="catalog-action-button is-buy"
                onClick={handleCheckout}
                disabled={isProcessing || Boolean(pendingPayment)}
              >
                {isProcessing ? "Opening Checkout..." : "Pay with Razorpay"}
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
