/*
 * File: MyCoursesPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner dashboard with searchable course cards and profile insights.
 * What it is: The new landing page for the learner's course catalog and gamified profile panel.
 */
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import SearchBar from "../components/SearchBar";
import CourseGrid from "../components/CourseGrid";
import ProfilePanel from "../components/ProfilePanel";
import { learnerProfileMock, myCoursesMock } from "../data/myCoursesMock";
import { useState } from "react";

export default function MyCoursesPage({ theme, toggleTheme }) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();

  const filteredCourses = myCoursesMock.filter((course) => {
    if (!normalizedQuery) {
      return true;
    }

    const searchTarget = [
      course.title,
      course.shortDescription,
      ...course.tags,
    ]
      .join(" ")
      .toLowerCase();

    return searchTarget.includes(normalizedQuery);
  });

  return (
    <main className="course-page-shell">
      <Navbar
        brandName="KaiCrypt"
        learnerName={learnerProfileMock.learnerName}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="course-page-card my-courses-shell">
        <div className="my-courses-header">
          <div className="my-courses-heading">
            <span className="eyebrow">Learner Dashboard</span>
            <Link className="my-courses-title-link" to="/my-courses">
              <h1>My Courses</h1>
            </Link>
          </div>

          <SearchBar
            value={query}
            onChange={setQuery}
            placeholder="Search all courses"
          />
        </div>

        <div className="my-courses-layout">
          <CourseGrid courses={filteredCourses} />
          <ProfilePanel profile={learnerProfileMock} />
        </div>
      </div>
    </main>
  );
}
