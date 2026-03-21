/*
 * File: CourseDetailPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner-facing course overview screen for an enrolled course.
 * What it is: Page-level container that wires mock course data into the overview layout and title search.
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import CourseHeader from "../components/CourseHeader";
import CourseTabs from "../components/CourseTabs";
import ContentSearch from "../components/ContentSearch";
import ContentList from "../components/ContentList";
import { getCourseDetailMock } from "../data/courseDetailMock";

export default function CourseDetailPage() {
  const { courseId = "odoo-crm" } = useParams();
  const [query, setQuery] = useState("");
  // Mock data is used for now so the UI can be reviewed before backend integration.
  const course = getCourseDetailMock(courseId);

  // Search only narrows the visible list. Progress numbers remain course-wide.
  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = course.contentItems
    .filter((item) =>
      normalizedQuery ? item.title.toLowerCase().includes(normalizedQuery) : true,
    )
    .sort((left, right) => left.order - right.order);

  return (
    <main className="course-page-shell">
      <Navbar brandName={course.providerName} learnerName={course.learnerName} />

      <div className="course-page-card">
        <CourseHeader course={course} />

        <div className="course-toolbar">
          <CourseTabs courseId={course.id} />
          <ContentSearch value={query} onChange={setQuery} />
        </div>

        <ContentList
          items={filteredItems}
          totalCount={course.progress.totalCount}
        />
      </div>
    </main>
  );
}
