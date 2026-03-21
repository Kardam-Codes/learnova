/*
 * File: LessonPlayerPage.jsx
 * Owner: KARDAM
 * Purpose: Render the route-driven learning shell for document, video, and quiz content.
 * What it is: A fullscreen learner player with a persistent sidebar, iframe viewers, quiz subflow, and reward state.
 */
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCourseDetailMock } from "../data/courseDetailMock";
import { buildLearningRoute, buildQuizQuestionRoute, buildQuizRewardRoute } from "../utils/learningRoutes";
import { LEARNING_CONTENT_MODE } from "../../shared/types/common_types";

function BackArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M14.5 5 7.5 12l7 7" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8.5 12h9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M5 7h14M5 12h14M5 17h14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function AttachmentIcon() {
  return (
    <svg viewBox="0 0 24 24" className="attachment-icon" aria-hidden="true">
      <path d="M8 8.5v7.5a4 4 0 0 0 8 0V6.8a2.8 2.8 0 0 0-5.6 0v8.8a1.3 1.3 0 0 0 2.6 0V8.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SidebarStatusIcon({ status }) {
  if (status === "completed") {
    return (
      <span className="learning-status is-completed" aria-hidden="true">
        <svg viewBox="0 0 24 24" className="status-check-icon">
          <path d="M6 12.5 10 16.5 18 7.5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }

  if (status === "in_progress") {
    return <span className="learning-status is-current" aria-hidden="true" />;
  }

  return <span className="learning-status is-pending" aria-hidden="true" />;
}

function LearningSidebar({ course, currentContentId, isOpen, onToggle }) {
  return (
    <aside className={`learning-sidebar ${isOpen ? "" : "is-collapsed"}`}>
      <div className="learning-sidebar-top">
        {isOpen ? (
          <Link className="learning-back-button" to={`/courses/${course.id}`}>
            <BackArrowIcon />
            <span>Back</span>
          </Link>
        ) : null}
        <button
          type="button"
          className="learning-menu-button"
          aria-label={isOpen ? "Collapse content sidebar" : "Expand content sidebar"}
          aria-expanded={isOpen}
          onClick={onToggle}
        >
          <MenuIcon />
        </button>
      </div>

      {isOpen ? (
        <>
          <div className="learning-course-card">
            <h2>{course.title}</h2>
            <div className="learning-progress-track">
              <span
                className="learning-progress-fill"
                style={{ width: `${course.progress.completionPercentage}%` }}
              />
            </div>
            <p>{course.progress.completionPercentage}% Completed</p>
          </div>

          <div className="learning-outline">
            {course.contentItems.map((item) => (
              <Link
                key={item.id}
                className={`learning-outline-item ${item.id === currentContentId ? "is-active" : ""}`}
                to={buildLearningRoute(course.id, item)}
              >
                <div className="learning-outline-copy">
                  <span className="learning-outline-title">{item.title}</span>
                  {item.attachments?.length ? (
                    <div className="learning-attachments">
                      {item.attachments.map((attachment) => (
                        <span className="learning-attachment-label" key={attachment.id}>
                          <AttachmentIcon />
                          <span>{attachment.label}</span>
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <SidebarStatusIcon status={item.status} />
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </aside>
  );
}

function LearningFooterAction({ label, to }) {
  return (
    <Link className="learning-footer-button" to={to}>
      <span>{label}</span>
      <BackArrowIcon />
    </Link>
  );
}

function QuizChoices({ question, selectedIndex }) {
  return (
    <div className="quiz-options">
      {question.options.map((option, optionIndex) => (
        <label className="quiz-option" key={option}>
          <span className={`quiz-radio ${selectedIndex === optionIndex ? "is-selected" : ""}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
  );
}

function LearningMainContent({ course, contentItem, questionIndex, pathname }) {
  const questionNumber = questionIndex === null ? null : Number(questionIndex);
  const questions = contentItem.quizQuestions ?? [];
  const currentQuestion = questionNumber === null ? null : questions[questionNumber];
  const isRewardRoute = pathname.endsWith("/reward");
  const isQuizQuestionRoute = pathname.includes("/question/");
  const nextContent = contentItem.nextContentId
    ? course.contentItems.find((item) => item.id === contentItem.nextContentId)
    : null;

  if (contentItem.mode === LEARNING_CONTENT_MODE.DOCUMENT) {
    return (
      <>
        <div className="learning-description-strip">{contentItem.description}</div>
        <section className="learning-viewer-card">
          <h1>Document</h1>
          <iframe src={contentItem.contentUrl} title={contentItem.title} className="learning-iframe" />
        </section>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Next Content" : "Complete this course"}
            to={nextContent ? buildLearningRoute(course.id, nextContent) : `/courses/${course.id}`}
          />
        </div>
      </>
    );
  }

  if (contentItem.mode === LEARNING_CONTENT_MODE.VIDEO) {
    return (
      <>
        <div className="learning-description-strip">{contentItem.description}</div>
        <section className="learning-viewer-card">
          <h1>{contentItem.title}</h1>
          <iframe src={contentItem.contentUrl} title={contentItem.title} className="learning-iframe" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
        </section>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Next Content" : "Complete this course"}
            to={nextContent ? buildLearningRoute(course.id, nextContent) : `/courses/${course.id}`}
          />
        </div>
      </>
    );
  }

  if (isRewardRoute) {
    return (
      <>
        <div className="learning-reward-overlay">
          <section className="learning-reward-card">
            <button type="button" className="reward-close-button" aria-label="Close reward modal">
              <svg viewBox="0 0 24 24" className="inline-icon">
                <path d="M7 7 17 17M17 7 7 17" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" />
              </svg>
            </button>
            <h1>Bingo! You have earned!</h1>
            <p>{contentItem.reward?.pointsEarned ?? 0} points</p>
            <div className="reward-progress-track">
              <span
                className="reward-progress-fill"
                style={{
                  width: `${Math.min(((contentItem.reward?.pointsEarned ?? 0) / (contentItem.reward?.nextTarget ?? 100)) * 100, 100)}%`,
                }}
              />
            </div>
            <div className="reward-scale">
              <span>5 Points</span>
              <span>{contentItem.reward?.nextTarget ?? 100} Points</span>
            </div>
            <p className="reward-message">{contentItem.reward?.message}</p>
          </section>
        </div>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Complete this course" : "Complete this course"}
            to={nextContent ? buildLearningRoute(course.id, nextContent) : `/courses/${course.id}`}
          />
        </div>
      </>
    );
  }

  if (!isQuizQuestionRoute) {
    return (
      <>
        <section className="quiz-intro-card">
          <div className="quiz-intro-copy">
            <p>- Total Questions '{contentItem.quizRules?.totalQuestions ?? questions.length}'</p>
            <p>- Multiple Attempts</p>
          </div>
          <Link className="catalog-action-button is-continue quiz-main-button" to={buildQuizQuestionRoute(course.id, contentItem.id, 0)}>
            Start Quiz
          </Link>
        </section>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Next Content" : "Complete this course"}
            to={nextContent ? buildLearningRoute(course.id, nextContent) : `/courses/${course.id}`}
          />
        </div>
      </>
    );
  }

  const isFinalQuestion = questionNumber === questions.length - 1;
  const proceedLabel = isFinalQuestion ? "Proceed and Complete Quiz" : "Proceed";
  const proceedTo = isFinalQuestion
    ? buildQuizRewardRoute(course.id, contentItem.id)
    : buildQuizQuestionRoute(course.id, contentItem.id, questionNumber + 1);

  return (
    <>
      <section className="quiz-question-card">
        <div className="quiz-question-meta">
          <span>Question</span>
          <strong>
            {questionNumber + 1} of {questions.length}
          </strong>
        </div>
        <div className="quiz-question-prompt">{currentQuestion?.prompt}</div>
        <QuizChoices question={currentQuestion} selectedIndex={1} />
        <Link className="catalog-action-button is-start quiz-main-button" to={proceedTo}>
          {proceedLabel}
        </Link>
      </section>
      <div className="learning-footer-actions">
        <LearningFooterAction
          label={isFinalQuestion ? "Complete this course" : "Next Content"}
          to={
            isFinalQuestion
              ? `/courses/${course.id}`
              : nextContent
                ? buildLearningRoute(course.id, nextContent)
                : `/courses/${course.id}`
          }
        />
      </div>
    </>
  );
}

export default function LessonPlayerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { courseId, contentId, mode, questionIndex } = useParams();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const course = getCourseDetailMock(courseId);
  const contentItem = course.contentItems.find((item) => item.id === contentId) ?? course.contentItems[0];

  useEffect(() => {
    if (mode && contentItem.mode !== mode && !(mode === LEARNING_CONTENT_MODE.QUIZ && contentItem.mode === LEARNING_CONTENT_MODE.QUIZ)) {
      navigate(buildLearningRoute(course.id, contentItem), { replace: true });
    }
  }, [contentItem, course.id, mode, navigate]);

  return (
    <main className="learning-page-shell">
      <div className={`learning-player-frame ${isSidebarOpen ? "" : "is-sidebar-collapsed"}`}>
        <LearningSidebar
          course={course}
          currentContentId={contentItem.id}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen((current) => !current)}
        />
        <section className="learning-main-panel">
          <LearningMainContent
            course={course}
            contentItem={contentItem}
            questionIndex={questionIndex ?? null}
            pathname={location.pathname}
          />
        </section>
      </div>
    </main>
  );
}
