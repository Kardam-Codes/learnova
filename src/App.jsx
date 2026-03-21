/*
 * File: App.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Define the full frontend route map for learner and instructor flows.
 * What it is: The top-level React router configuration that wires all page-level screens into the app.
 */
import { Navigate, Route, Routes } from "react-router-dom";
import MyCoursesPage from "./pages/MyCoursesPage";
import CourseDetailPage from "./pages/CourseDetailPage";
import CourseReviewsPage from "./pages/CourseReviewsPage";
import LessonPlayerPage from "./pages/LessonPlayerPage";
import PaymentFlowPage from "./pages/PaymentFlowPage";
import InstructorDashboard from "./pages/InstructorDashboard";
import CourseConfig from "./pages/CourseConfig";
import ReportingDashboardPage from "./pages/ReportingDashboardPage";
import QuizBuilderPage from "./pages/QuizBuilderPage";
import LessonContentEditorPage from "./pages/LessonContentEditorPage";

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

      {/* Instructor and organiser pages are grouped under a dedicated route prefix. */}
      <Route
        path="/instructor"
        element={<Navigate to="/instructor/courses" replace />}
      />
      <Route path="/instructor/courses" element={<InstructorDashboard />} />
      <Route path="/instructor/courses/:courseId/edit" element={<CourseConfig />} />
      <Route path="/instructor/reports" element={<ReportingDashboardPage />} />
      <Route
        path="/instructor/quizzes/:quizId/builder"
        element={<QuizBuilderPage />}
      />
      <Route
        path="/instructor/content/:contentId/edit"
        element={<LessonContentEditorPage />}
      />
    </Routes>
  );
}
