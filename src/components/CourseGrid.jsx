/*
 * File: CourseGrid.jsx
 * Owner: KARDAM
 * Purpose: Render the searchable list of course cards.
 * What it is: A grid wrapper that maps course data into reusable CourseCard components.
 */
import CourseCard from "./CourseCard";

export default function CourseGrid({ courses }) {
  return (
    <section className="catalog-grid-shell">
      <div className="catalog-grid">
        {courses.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>

      {courses.length === 0 ? (
        <div className="catalog-empty-state">
          No course matched your search. Try a different course title or tag.
        </div>
      ) : null}
    </section>
  );
}
