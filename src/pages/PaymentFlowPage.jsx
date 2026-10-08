/*
 * File: PaymentFlowPage.jsx
 * Owner: KARDAM
 * Purpose: Run the learner-side paid course checkout flow.
 * What it is: A Razorpay-backed payment page that creates orders, launches checkout, and verifies successful payments.
 */
import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import StatusBanner from "../components/StatusBanner";
import LoadingBlock from "../components/LoadingBlock";
import {
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

  const handleCheckout = async () => {
    setIsProcessing(true);
    setError("");
    setMessage("");

    try {
      const RazorpayCheckout = await loadRazorpayCheckout();
      const order = await createCoursePaymentOrderRequest(courseId, token);

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
        handler: async (response) => {
          try {
            await verifyCoursePaymentRequest(courseId, token, {
              razorpayOrderId: response.razorpay_order_id,
              razorpayPaymentId: response.razorpay_payment_id,
              razorpaySignature: response.razorpay_signature,
            });
            setMessage("Payment successful. The course is now unlocked for you.");
            navigate(`/courses/${courseId}`);
          } catch (verifyError) {
            setError(verifyError.message || "Payment was captured but verification failed.");
          }
        },
        modal: {
          ondismiss: () => {
            setIsProcessing(false);
          },
        },
      });

      razorpay.open();
    } catch (checkoutError) {
      setError(checkoutError.message || "Checkout could not be started.");
    } finally {
      setIsProcessing(false);
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
                disabled={isProcessing}
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
