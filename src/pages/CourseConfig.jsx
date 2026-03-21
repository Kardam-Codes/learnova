/*
 * File: CourseConfig.jsx
 * Owner: YUG
 * Purpose: Render the instructor course configuration page with screenshot-aligned tabs and actions.
 * What it is: A route-level admin page for editing live course metadata, content, options, quizzes, and attendees.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { getCourseConfigMock } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import {
  addAdminCourseAttendeesRequest,
  createAdminCourseRequest,
  fetchAdminCourseAttendeesRequest,
  fetchAdminCourseContentRequest,
  fetchAdminCourseQuizzesRequest,
  fetchAdminCourseRequest,
  publishAdminCourseRequest,
  updateAdminCourseRequest,
} from "../utils/apiClient";

const tabs = ["Content", "Description", "Options", "Quiz"];
const courseAdmins = ["Yug", "Salman Khan", "Kardam"];

const emptyCourse = {
  slug: "new-course",
  title: "",
  shortDescription: "",
  description: "",
  thumbnailUrl: "",
  coverImageUrl: "",
  websiteId: "",
  visibility: "everyone",
  accessRule: "open",
  price: 0,
  isPublished: false,
  responsibleUserId: null,
  tags: [],
};

function PublishControl({ isPublished, onToggle }) {
  return (
    <div className="publish-card">
      <button type="button" className="publish-row" onClick={onToggle}>
        <span>{isPublished ? "Published on website" : "Publish on website"}</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <polyline points="5 13 10 18 19 6" />
        </svg>
      </button>

      <div className="publish-row publish-row-toggle">
        <span>Share on web</span>
        <span className={`publish-switch${isPublished ? " is-on" : ""}`} aria-hidden="true">
          <span />
        </span>
      </div>
    </div>
  );
}

function mapCourseToFormState(course) {
  return {
    slug: course.slug,
    title: course.title ?? "",
    shortDescription: course.shortDescription ?? "",
    description: course.description ?? "",
    thumbnailUrl: course.thumbnailUrl ?? "",
    coverImageUrl: course.coverImageUrl ?? "",
    websiteId: course.websiteId ?? "",
    visibility: course.visibility ?? "everyone",
    accessRule: course.accessRule ?? "open",
    price: course.price ?? 0,
    isPublished: Boolean(course.isPublished),
    responsibleUserId: course.responsibleUserId ?? null,
    tags: course.tags ?? [],
  };
}

export default function CourseConfig() {
  const { courseId = "odoo-crm" } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const fallbackCourse = useMemo(() => getCourseConfigMock(courseId), [courseId]);
  const [activeTab, setActiveTab] = useState("Content");
  const [courseForm, setCourseForm] = useState(() => ({
    ...emptyCourse,
    title: fallbackCourse.title,
    shortDescription: fallbackCourse.description,
    description: fallbackCourse.description,
    tags: fallbackCourse.tags,
    isPublished: fallbackCourse.isPublished,
  }));
  const [contentItems, setContentItems] = useState([]);
  const [quizzes, setQuizzes] = useState([]);
  const [attendees, setAttendees] = useState([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [loadError, setLoadError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const isNewCourse = courseId === "new-course";

  useEffect(() => {
    let isMounted = true;

    const loadCourse = async () => {
      if (isNewCourse) {
        setCourseForm((current) => ({
          ...current,
          ...emptyCourse,
        }));
        setContentItems([]);
        setQuizzes([]);
        setAttendees([]);
        return;
      }

      try {
        const [courseResponse, contentResponse, quizResponse, attendeeResponse] =
          await Promise.all([
            fetchAdminCourseRequest(courseId, token),
            fetchAdminCourseContentRequest(courseId, token),
            fetchAdminCourseQuizzesRequest(courseId, token),
            fetchAdminCourseAttendeesRequest(courseId, token),
          ]);

        if (!isMounted) {
          return;
        }

        setCourseForm(mapCourseToFormState(courseResponse));
        setContentItems(contentResponse.contentItems);
        setQuizzes(quizResponse.quizzes);
        setAttendees(attendeeResponse.attendees);
        setLoadError("");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setLoadError(error.message);
      }
    };

    if (token) {
      loadCourse();
    }

    return () => {
      isMounted = false;
    };
  }, [courseId, isNewCourse, token]);

  const updateField = (fieldName, value) => {
    setCourseForm((current) => ({
      ...current,
      [fieldName]: value,
    }));
  };

  const handleSaveCourse = async () => {
    setIsSaving(true);
    setStatusMessage("");

    const payload = {
      title: courseForm.title,
      shortDescription: courseForm.shortDescription,
      description: courseForm.description,
      thumbnailUrl: courseForm.thumbnailUrl || null,
      coverImageUrl: courseForm.coverImageUrl || null,
      websiteId: courseForm.websiteId || null,
      visibility: courseForm.visibility,
      accessRule: courseForm.accessRule,
      price: Number(courseForm.price) || 0,
      responsibleUserId: courseForm.responsibleUserId,
      tags: courseForm.tags,
      isPublished: courseForm.isPublished,
    };

    try {
      const response = isNewCourse
        ? await createAdminCourseRequest(token, payload)
        : await updateAdminCourseRequest(courseId, token, payload);

      setCourseForm(mapCourseToFormState(response));
      setStatusMessage("Course saved successfully.");

      if (isNewCourse || response.slug !== courseId) {
        navigate(`/instructor/courses/${response.slug}/edit`, { replace: true });
      }
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTogglePublish = async () => {
    if (isNewCourse) {
      setCourseForm((current) => ({
        ...current,
        isPublished: !current.isPublished,
      }));
      return;
    }

    try {
      const response = await publishAdminCourseRequest(
        courseForm.slug,
        token,
        !courseForm.isPublished,
      );
      setCourseForm(mapCourseToFormState(response));
      setStatusMessage(response.isPublished ? "Course published." : "Course moved to draft.");
    } catch (error) {
      setStatusMessage(error.message);
    }
  };

  const handleAddAttendee = async () => {
    const email = window.prompt("Enter attendee email");
    const name = window.prompt("Enter attendee name");

    if (!email || !name) {
      return;
    }

    try {
      const response = await addAdminCourseAttendeesRequest(courseForm.slug, token, {
        attendees: [
          {
            email,
            name,
            enrollmentSource: "invited",
            paymentStatus: courseForm.accessRule === "payment" ? "pending" : "not_required",
          },
        ],
      });
      setAttendees((current) => [...current, ...response.attendees]);
      setStatusMessage("Attendee added successfully.");
    } catch (error) {
      setStatusMessage(error.message);
    }
  };

  const handleContactAttendees = () => {
    if (!attendees.length) {
      setStatusMessage("No attendees are available to contact yet.");
      return;
    }

    const mailtoList = attendees
      .map((attendee) => attendee.email)
      .filter(Boolean)
      .join(",");

    const subject = encodeURIComponent(`Learnova update: ${courseForm.title || "Course update"}`);
    window.location.href = `mailto:${mailtoList}?subject=${subject}`;
  };

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="instructor-form-shell">
          <div className="instructor-top-actions">
            <Link
              to="/instructor/courses/new-course/edit"
              className="catalog-action-button instructor-solid-button"
            >
              New
            </Link>

            <div className="inline-button-row">
              <button
                type="button"
                className="catalog-action-button instructor-ghost-button"
                onClick={handleContactAttendees}
              >
                Contact Attendees
              </button>
              <button
                type="button"
                className="catalog-action-button instructor-ghost-button"
                onClick={handleAddAttendee}
                disabled={isNewCourse}
              >
                Add Attendees
              </button>
            </div>

            <div className="inline-button-row instructor-top-right">
              <PublishControl
                isPublished={courseForm.isPublished}
                onToggle={handleTogglePublish}
              />
              {!isNewCourse ? (
                <Link
                  to={`/courses/${courseForm.slug}`}
                  className="catalog-action-button instructor-ghost-button"
                >
                  Preview
                </Link>
              ) : null}
              <button
                type="button"
                className="catalog-action-button instructor-cta-button"
                onClick={handleSaveCourse}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save Course"}
              </button>
            </div>
          </div>

          {statusMessage ? <p className="content-empty">{statusMessage}</p> : null}
          {loadError ? <p className="content-empty">{loadError}</p> : null}

          <div className="course-config-hero course-config-hero-compact">
            <div className="course-config-copy">
              <label className="instructor-field instructor-field-line">
                <span>Course Title:</span>
                <input
                  type="text"
                  value={courseForm.title}
                  onChange={(event) => updateField("title", event.target.value)}
                />
              </label>

              <label className="instructor-field instructor-field-line">
                <span>Short Description:</span>
                <input
                  type="text"
                  value={courseForm.shortDescription}
                  onChange={(event) => updateField("shortDescription", event.target.value)}
                />
              </label>

              <label className="instructor-field instructor-field-line">
                <span>Tags:</span>
                <input
                  type="text"
                  value={courseForm.tags.join(", ")}
                  onChange={(event) =>
                    updateField(
                      "tags",
                      event.target.value
                        .split(",")
                        .map((tag) => tag.trim())
                        .filter(Boolean),
                    )
                  }
                />
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
              <strong>Course image</strong>
              <input
                type="text"
                value={courseForm.thumbnailUrl}
                onChange={(event) => updateField("thumbnailUrl", event.target.value)}
                placeholder="Thumbnail URL"
              />
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

                  {contentItems.map((item) => (
                    <div key={item.id} className="instructor-table-row">
                      <span>{item.title}</span>
                      <span>{item.contentMode}</span>
                      <div className="row-actions">
                        <Link
                          to={`/instructor/content/${item.slug}/edit?course=${courseForm.slug}`}
                          className="row-menu-button"
                          aria-label={`Edit ${item.title}`}
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
                  to={`/instructor/content/new-content/edit?course=${courseForm.slug}`}
                  className="catalog-action-button instructor-cta-button"
                >
                  Add Content
                </Link>
              </section>
            ) : null}

            {activeTab === "Description" ? (
              <section className="description-panel course-description-panel">
                <textarea
                  className="editor-description-textarea"
                  value={courseForm.description}
                  onChange={(event) => updateField("description", event.target.value)}
                />
              </section>
            ) : null}

            {activeTab === "Options" ? (
              <section className="options-panel-grid options-panel-grid-sketched">
                <div className="option-box option-box-sketched option-box-left">
                  <h3>Access course rights</h3>

                  <label className="instructor-field options-select-field options-select-field-sketched">
                    <span>Show course to:</span>
                    <select
                      value={courseForm.visibility}
                      onChange={(event) => updateField("visibility", event.target.value)}
                    >
                      <option value="everyone">Everyone</option>
                      <option value="signed_in">Signed In</option>
                    </select>
                  </label>

                  <div className="options-checkbox-row options-checkbox-row-sketched">
                    <span>Access rules:</span>
                    {[
                      { value: "open", label: "Open" },
                      { value: "invitation", label: "On Invitation" },
                      { value: "payment", label: "On Payment" },
                    ].map((option) => (
                      <label key={option.value}>
                        <input
                          type="radio"
                          name="access-rule"
                          checked={courseForm.accessRule === option.value}
                          onChange={() => updateField("accessRule", option.value)}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                    <label className="instructor-field option-price-field-sketched">
                      <span>Price:</span>
                      <input
                        type="number"
                        value={courseForm.price}
                        onChange={(event) => updateField("price", event.target.value)}
                      />
                    </label>
                  </div>
                </div>

                <div className="option-box option-box-sketched option-box-right">
                  <h3>Responsible</h3>

                  <label className="instructor-field instructor-field-line options-responsible-field">
                    <span>Website Id:</span>
                    <input
                      type="text"
                      value={courseForm.websiteId}
                      onChange={(event) => updateField("websiteId", event.target.value)}
                    />
                  </label>

                  <label className="instructor-field options-admin-field options-admin-field-sketched">
                    <span>Course Admin:</span>
                    <select
                      value={courseForm.responsibleUserId ?? ""}
                      onChange={(event) => updateField("responsibleUserId", event.target.value || null)}
                    >
                      <option value="">Unassigned</option>
                      {courseAdmins.map((admin) => (
                        <option key={admin} value="">
                          {admin}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="profile-current-badge">
                    <span className="eyebrow">Attendees</span>
                    <strong>{attendees.length}</strong>
                  </div>
                </div>
              </section>
            ) : null}

            {activeTab === "Quiz" ? (
              <section className="instructor-table-shell">
                <div className="instructor-table">
                  <div className="instructor-table-head">
                    <span>Quiz title</span>
                    <span>Questions</span>
                    <span />
                  </div>

                  {quizzes.map((quiz) => (
                    <div key={quiz.id} className="instructor-table-row">
                      <span>{quiz.title}</span>
                      <span>{quiz.questions.length}</span>
                      <div className="row-actions">
                        <Link
                          to={`/instructor/quizzes/${quiz.id}/builder?course=${courseForm.slug}`}
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
                  to={`/instructor/quizzes/new-quiz/builder?course=${courseForm.slug}`}
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
