/*
 * File: App.jsx
 * Owner: KARDAM
 * Purpose: Define the learner frontend route map.
 * What it is: The top-level React router configuration for course overview, reviews, and player pages.
 */
import { Navigate, Route, Routes } from "react-router-dom";
import MyCoursesPage from "./pages/MyCoursesPage";
import CourseDetailPage from "./pages/CourseDetailPage";
import CourseReviewsPage from "./pages/CourseReviewsPage";
import LessonPlayerPage from "./pages/LessonPlayerPage";
import PaymentFlowPage from "./pages/PaymentFlowPage";

export default function App() {
  return (
    <Routes>
      {/* Default entry goes to the learner's main course dashboard. */}
      <Route path="/" element={<Navigate to="/my-courses" replace />} />
      {/* My Courses is the dashboard page with the course grid and profile panel. */}
      <Route path="/my-courses" element={<MyCoursesPage />} />
      {/* Main learner-facing course overview page. */}
      <Route path="/courses/:courseId" element={<CourseDetailPage />} />
      {/* Separate reviews route planned as its own page. */}
      <Route path="/courses/:courseId/reviews" element={<CourseReviewsPage />} />
      {/* Paid course CTA opens a dedicated payment placeholder route. */}
      <Route path="/courses/:courseId/payment" element={<PaymentFlowPage />} />
      {/* Placeholder player route so each content row has a real destination. */}
      <Route
        path="/courses/:courseId/content/:contentId"
        element={<LessonPlayerPage />}
      />
    </Routes>
  );
}
