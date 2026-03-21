/*
 * File: CourseConfig.jsx
 * Owner: YUG
 * Purpose: Render the instructor course configuration page with screenshot-aligned tabs and actions.
 * What it is: A route-level admin page for editing course metadata, content, options, and quiz links.
 */
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { getCourseConfigMock } from "../data/instructorMock";

const tabs = ["Content", "Description", "Options", "Quiz"];
const courseAdmins = ["Yug", "Salman Khan", "Kardam"];

function PublishControl({ shareOnWeb }) {
  return (
    <div className="publish-card">
      <div className="publish-row">
        <span>Publish on website</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <polyline points="5 13 10 18 19 6" />
        </svg>
      </div>

      <div className="publish-row publish-row-toggle">
        <span>Share on web</span>
        <span className={`publish-switch${shareOnWeb ? " is-on" : ""}`} aria-hidden="true">
          <span />
        </span>
      </div>
    </div>
  );
}

export default function CourseConfig() {
  const { courseId = "odoo-crm" } = useParams();
  const course = useMemo(() => getCourseConfigMock(courseId), [courseId]);
  const [activeTab, setActiveTab] = useState("Content");

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="instructor-form-shell">
          <div className="instructor-top-actions">
            <Link to="/instructor/courses/new-course/edit" className="catalog-action-button instructor-solid-button">
              New
            </Link>

            <div className="inline-button-row">
              <button type="button" className="catalog-action-button instructor-ghost-button">
                Contact Attendees
              </button>
              <button type="button" className="catalog-action-button instructor-ghost-button">
                Add Attendees
              </button>
            </div>

            <div className="inline-button-row instructor-top-right">
              <PublishControl shareOnWeb={course.shareOnWeb} />
              <Link to={`/courses/${course.id}`} className="catalog-action-button instructor-ghost-button">
                Preview
              </Link>
            </div>
          </div>

          <div className="course-config-hero course-config-hero-compact">
            <div className="course-config-copy">
              <label className="instructor-field instructor-field-line">
                <span>Course Title:</span>
                <input type="text" defaultValue={course.title} />
              </label>

              <label className="instructor-field instructor-field-line">
                <span>Tags:</span>
                <input type="text" defaultValue={course.tags.join(", ")} />
              </label>
            </div>

            <aside className="course-image-card">
              <div className="course-image-actions">
                <button type="button" aria-label="Edit image">
                  <svg viewBox="0 0 24 24">
                    <path d="M4 16.5V20h3.5L18 9.5 14.5 6 4 16.5z" />
                    <path d="M13 7.5 16.5 11" />
                  </svg>
                </button>
                <button type="button" aria-label="Delete image">
                  <svg viewBox="0 0 24 24">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M8 6V4h8v2" />
                    <path d="M19 6l-1 14H6L5 6" />
                  </svg>
                </button>
              </div>
              <strong>{course.imageLabel}</strong>
            </aside>
          </div>

          <div className="instructor-tab-row" role="tablist" aria-label="Course configuration tabs">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                className={`course-tab${activeTab === tab ? " is-active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="instructor-panel">
            {activeTab === "Content" ? (
              <section className="instructor-table-shell">
                <div className="instructor-table instructor-content-table">
                  <div className="instructor-table-head">
                    <span>Content title</span>
                    <span>Category</span>
                    <span />
                  </div>

                  {course.contentItems.map((item) => (
                    <div key={item.id} className="instructor-table-row">
                      <span>{item.title}</span>
                      <span>{item.category}</span>
                      <div className="row-actions">
                        {item.category === "Quiz" ? (
                          <Link
                            to="/instructor/quizzes/crm-quiz/builder"
                            className="row-menu-button"
                            aria-label={`Open ${item.title}`}
                          >
                            <svg viewBox="0 0 24 24">
                              <circle cx="12" cy="5" r="2" />
                              <circle cx="12" cy="12" r="2" />
                              <circle cx="12" cy="19" r="2" />
                            </svg>
                          </Link>
                        ) : (
                          <Link
                            to={`/instructor/content/${item.id}/edit`}
                            className="row-menu-button"
                            aria-label={`Edit ${item.title}`}
                          >
                            <svg viewBox="0 0 24 24">
                              <circle cx="12" cy="5" r="2" />
                              <circle cx="12" cy="12" r="2" />
                              <circle cx="12" cy="19" r="2" />
                            </svg>
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <Link
                  to="/instructor/content/video-advanced-sales/edit"
                  className="catalog-action-button instructor-cta-button"
                >
                  Add Content
                </Link>
              </section>
            ) : null}

            {activeTab === "Description" ? (
              <section className="description-panel course-description-panel">
                <p>{course.description}</p>
              </section>
            ) : null}

            {activeTab === "Options" ? (
              <section className="options-panel-grid options-panel-grid-sketched">
                <div className="option-box option-box-sketched option-box-left">
                  <h3>Access course rights</h3>

                  <label className="instructor-field options-select-field options-select-field-sketched">
                    <span>Show course to:</span>
                    <select defaultValue={course.visibility}>
                      <option>Everyone</option>
                      <option>Signed In</option>
                    </select>
                  </label>

                  <div className="options-checkbox-row options-checkbox-row-sketched">
                    <span>Access rules:</span>
                    <label>
                      <input type="checkbox" defaultChecked={course.accessRules.open} />
                      <span>Open</span>
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        defaultChecked={course.accessRules.invitation}
                      />
                      <span>On Invitation</span>
                    </label>
                    <label className="options-payment-row">
                      <input type="checkbox" defaultChecked={course.accessRules.payment} />
                      <span>On Payment</span>
                    </label>
                    <label className="instructor-field option-price-field-sketched">
                      <span>Price:</span>
                      <input type="text" defaultValue={course.price} />
                    </label>
                  </div>
                </div>

                <div className="option-box option-box-sketched option-box-right">
                  <h3>Responsible</h3>

                  <label className="instructor-field instructor-field-line options-responsible-field">
                    <span>Responsible:</span>
                    <input type="text" defaultValue={course.responsible} />
                  </label>

                  <label className="instructor-field options-admin-field options-admin-field-sketched">
                    <span>Course Admin:</span>
                    <select defaultValue={course.courseAdmin}>
                      {courseAdmins.map((admin) => (
                        <option key={admin}>{admin}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </section>
            ) : null}

            {activeTab === "Quiz" ? (
              <section className="instructor-table-shell">
                <div className="instructor-table">
                  <div className="instructor-table-head">
                    <span>Content title</span>
                    <span>Category</span>
                    <span />
                  </div>

                  {course.quizzes.map((quiz) => (
                    <div key={quiz.id} className="instructor-table-row">
                      <span>{quiz.title}</span>
                      <span>{quiz.category}</span>
                      <div className="row-actions">
                        <Link
                          to="/instructor/quizzes/crm-quiz/builder"
                          className="row-menu-button"
                          aria-label={`Open ${quiz.title}`}
                        >
                          <svg viewBox="0 0 24 24">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                          </svg>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>

                <Link
                  to="/instructor/quizzes/crm-quiz/builder"
                  className="catalog-action-button instructor-cta-button"
                >
                  Add Quiz
                </Link>
              </section>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
