/*
 * File: App.jsx
 * Owner: BOTH CAN ADD
 * Purpose: Define the full frontend route map for learner and instructor flows.
 * What it is: The top-level React router configuration and shared theme controller for learner and instructor pages.
 */
import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
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

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }

  return children;
}

export default function App() {
  // Light mode is the default, but users can switch themes from the shared navbar.
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
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/signup" element={<SignupPage />} />
      <Route path="/auth/forgot-password" element={<LoginPage />} />

      <Route path="/" element={<Navigate to="/my-courses" replace />} />
      <Route
        path="/my-courses"
        element={
          <ProtectedRoute>
            <MyCoursesPage theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/courses/:courseId"
        element={<CourseDetailPage theme={theme} toggleTheme={toggleTheme} />}
      />
      <Route
        path="/courses/:courseId/reviews"
        element={<CourseReviewsPage theme={theme} toggleTheme={toggleTheme} />}
      />
      <Route
        path="/courses/:courseId/payment"
        element={<PaymentFlowPage theme={theme} toggleTheme={toggleTheme} />}
      />
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

      {/* Instructor and organiser pages are grouped under a dedicated route prefix. */}
      <Route
        path="/instructor"
        element={
          <ProtectedRoute>
            <Navigate to="/instructor/courses" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instructor/courses"
        element={
          <ProtectedRoute>
            <InstructorDashboard theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instructor/courses/:courseId/edit"
        element={
          <ProtectedRoute>
            <CourseConfig theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instructor/reports"
        element={
          <ProtectedRoute>
            <ReportingDashboardPage theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instructor/quizzes/:quizId/builder"
        element={
          <ProtectedRoute>
            <QuizBuilderPage theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/instructor/content/:contentId/edit"
        element={
          <ProtectedRoute>
            <LessonContentEditorPage theme={theme} toggleTheme={toggleTheme} />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
