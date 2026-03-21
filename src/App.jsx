/*
 * File: App.jsx
 * Owner: KARDAM
 * Purpose: Define the learner frontend route map.
 * What it is: The top-level React router configuration and shared theme controller for learner pages.
 */
import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import MyCoursesPage from "./pages/MyCoursesPage";
import CourseDetailPage from "./pages/CourseDetailPage";
import CourseReviewsPage from "./pages/CourseReviewsPage";
import LessonPlayerPage from "./pages/LessonPlayerPage";
import PaymentFlowPage from "./pages/PaymentFlowPage";

export default function App() {
  // Light mode is the default, but learners can switch to dark mode from the navbar.
  const [theme, setTheme] = useState(() => {
    return window.localStorage.getItem("learnova-theme") ?? "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("learnova-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"));
  };

  return (
    <Routes>
      {/* Default entry goes to the learner's main course dashboard. */}
      <Route path="/" element={<Navigate to="/my-courses" replace />} />
      {/* My Courses is the dashboard page with the course grid and profile panel. */}
      <Route
        path="/my-courses"
        element={<MyCoursesPage theme={theme} toggleTheme={toggleTheme} />}
      />
      {/* Main learner-facing course overview page. */}
      <Route
        path="/courses/:courseId"
        element={<CourseDetailPage theme={theme} toggleTheme={toggleTheme} />}
      />
      {/* Separate reviews route planned as its own page. */}
      <Route
        path="/courses/:courseId/reviews"
        element={<CourseReviewsPage theme={theme} toggleTheme={toggleTheme} />}
      />
      {/* Paid course CTA opens a dedicated payment placeholder route. */}
      <Route
        path="/courses/:courseId/payment"
        element={<PaymentFlowPage theme={theme} toggleTheme={toggleTheme} />}
      />
      {/* Separate learn route states keep document, video, and quiz flows explicit. */}
      <Route
        path="/courses/:courseId/learn/:contentId/:mode"
        element={<LessonPlayerPage theme={theme} toggleTheme={toggleTheme} />}
      />
      <Route
        path="/courses/:courseId/learn/:contentId/quiz/question/:questionIndex"
        element={<LessonPlayerPage theme={theme} toggleTheme={toggleTheme} />}
      />
      <Route
        path="/courses/:courseId/learn/:contentId/quiz/reward"
        element={<LessonPlayerPage theme={theme} toggleTheme={toggleTheme} />}
      />
    </Routes>
  );
}
