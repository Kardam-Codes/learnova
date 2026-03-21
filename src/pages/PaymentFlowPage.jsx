/*
 * File: PaymentFlowPage.jsx
 * Owner: KARDAM
 * Purpose: Reserve the route opened by paid-course buy actions.
 * What it is: A placeholder payment page so Buy Course buttons already lead somewhere concrete.
 */
import { Link, useParams } from "react-router-dom";

export default function PaymentFlowPage() {
  const { courseId } = useParams();

  return (
    <main className="course-page-shell">
      <div className="course-page-card reviews-shell">
        <div className="reviews-header">
          <div>
            <span className="eyebrow">Payment Flow</span>
            <h2>{courseId}</h2>
          </div>
          <Link className="back-link" to="/my-courses">
            Back to My Courses
          </Link>
        </div>

        <section className="placeholder-panel">
          <span className="sticker">Next phase</span>
          <h3>Payment flow will be connected here.</h3>
          <p>
            The paid-course action is already routed so the checkout experience can
            be added without changing the course cards.
          </p>
        </section>
      </div>
    </main>
  );
}
