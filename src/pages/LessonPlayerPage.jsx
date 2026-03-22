/*
 * File: LessonPlayerPage.jsx
 * Owner: KARDAM
 * Purpose: Render the route-driven learning shell for document, video, and quiz content.
 * What it is: A fullscreen learner player with a persistent sidebar, iframe viewers, quiz subflow, and reward state.
 */
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { Suspense, lazy, useEffect, useState } from "react";
import { buildLearningRoute, buildQuizQuestionRoute, buildQuizRewardRoute } from "../utils/learningRoutes";
import { LEARNING_CONTENT_MODE } from "../../shared/types/common_types";
import EmptyState from "../components/EmptyState";
import LoadingBlock from "../components/LoadingBlock";
import StatusBanner from "../components/StatusBanner";
import { useAuth } from "../context/AuthContext";
import {
  fetchCourseContentRequest,
  fetchCourseDetailRequest,
  submitQuizAttemptRequest,
  updateCourseContentProgressRequest,
} from "../utils/apiClient";

const PDFViewer = lazy(() => import("../components/PDFViewer"));

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
  const getSidebarLockReason = (item) => {
    if (!course.isEnrolled) {
      return "Enroll to unlock";
    }

    if (item.mode === LEARNING_CONTENT_MODE.QUIZ) {
      return "Finish earlier lessons first";
    }

    return "Locked";
  };

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
              item.isLocked ? (
                <div
                  key={item.id}
                  className={`learning-outline-item is-locked ${item.id === currentContentId ? "is-active" : ""}`}
                  aria-label={`${item.title} is locked`}
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
                    <span className="learning-lock-reason">{getSidebarLockReason(item)}</span>
                  </div>
                  <SidebarStatusIcon status={item.status} />
                </div>
              ) : (
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
              )
            ))}
          </div>
        </>
      ) : null}
    </aside>
  );
}

function LearningFooterAction({ label, onClick, disabled = false }) {
  return (
    <button type="button" className="learning-footer-button" onClick={onClick} disabled={disabled}>
      <span>{label}</span>
      <BackArrowIcon />
    </button>
  );
}

function QuizChoices({ question, selectedIndexes, onSelect }) {
  const allowsMultipleAnswers = Boolean(question?.allowsMultipleAnswers);

  return (
    <div className="quiz-options">
      {question.options.map((option, optionIndex) => (
        <label className="quiz-option" key={`${question.id}-${optionIndex}`} onClick={() => onSelect(optionIndex)}>
          <span
            className={`quiz-radio ${selectedIndexes.includes(optionIndex) ? "is-selected" : ""} ${allowsMultipleAnswers ? "is-multiple" : ""}`}
          />
          <span>{option}</span>
        </label>
      ))}
    </div>
  );
}

function PDFViewerFallback() {
  return (
    <div className="pdf-viewer-shell">
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-group">
          <span className="pdf-toolbar-label">Preparing PDF...</span>
        </div>
      </div>
      <div className="pdf-canvas-shell">
        <div className="pdf-viewer-state">Loading PDF viewer...</div>
      </div>
    </div>
  );
}

function LearningMainContent({
  course,
  contentItem,
  questionIndex,
  pathname,
  quizSelections,
  onSelectQuizOption,
  onSubmitQuizAttempt,
  quizReward,
  isSubmittingQuiz,
  onCloseReward,
  onAdvanceContent,
}) {
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
          <h1>{contentItem.title}</h1>
          <Suspense fallback={<PDFViewerFallback />}>
            <PDFViewer fileUrl={contentItem.contentUrl} title={contentItem.title} />
          </Suspense>
        </section>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Next Content" : "Complete this course"}
            onClick={onAdvanceContent}
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
            onClick={onAdvanceContent}
          />
        </div>
      </>
    );
  }

  if (isRewardRoute) {
    const reward = quizReward ?? contentItem.reward;

    return (
      <>
        <div className="learning-reward-overlay">
          <section className="learning-reward-card">
            <button type="button" className="reward-close-button" aria-label="Close reward modal" onClick={onCloseReward}>
              <svg viewBox="0 0 24 24" className="inline-icon">
                <path d="M7 7 17 17M17 7 7 17" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" />
              </svg>
            </button>
            <h1>Bingo! You have earned!</h1>
            <p>{reward?.pointsEarned ?? 0} points</p>
            <div className="reward-progress-track">
              <span
                className="reward-progress-fill"
                style={{
                  width: `${Math.min(((reward?.pointsEarned ?? 0) / (reward?.nextTarget ?? 100)) * 100, 100)}%`,
                }}
              />
            </div>
            <div className="reward-scale">
              <span>5 Points</span>
              <span>{reward?.nextTarget ?? 100} Points</span>
            </div>
            <p className="reward-message">{reward?.message}</p>
          </section>
        </div>
        <div className="learning-footer-actions">
          <LearningFooterAction
            label={nextContent ? "Next Content" : "Complete this course"}
            onClick={onAdvanceContent}
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
            onClick={onAdvanceContent}
          />
        </div>
      </>
    );
  }

  const isFinalQuestion = questionNumber === questions.length - 1;
  const proceedLabel = isFinalQuestion ? "Proceed and Complete Quiz" : "Proceed";
  const selectedIndexes = currentQuestion
    ? quizSelections[currentQuestion.id] ?? []
    : [];
  const hasSelection = selectedIndexes.length > 0;

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
        <QuizChoices
          question={currentQuestion}
          selectedIndexes={selectedIndexes}
          onSelect={(optionIndex) => onSelectQuizOption(currentQuestion.id, optionIndex)}
        />
        <button
          type="button"
          className="catalog-action-button is-start quiz-main-button"
          onClick={() => onSubmitQuizAttempt({ isFinalQuestion, questionNumber })}
          disabled={!hasSelection || isSubmittingQuiz}
        >
          {proceedLabel}
        </button>
      </section>
    </>
  );
}

export default function LessonPlayerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { courseId, contentId, mode, questionIndex } = useParams();
  const { token } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [course, setCourse] = useState({
    id: courseId,
    title: "",
    progress: { completionPercentage: 0 },
    contentItems: [],
  });
  const [quizSelections, setQuizSelections] = useState({});
  const [quizReward, setQuizReward] = useState(null);
  const [isSubmittingQuiz, setIsSubmittingQuiz] = useState(false);
  const [contentOverride, setContentOverride] = useState(null);
  const [contentAccessError, setContentAccessError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [quizError, setQuizError] = useState("");
  const [isLoadingCourse, setIsLoadingCourse] = useState(true);

  useEffect(() => {
    // Clear previous content-specific state immediately when the route changes.
    setContentOverride(null);
    setQuizReward(null);
    setQuizSelections({});
  }, [contentId]);

  useEffect(() => {
    let isMounted = true;

    const loadCourse = async () => {
      setIsLoadingCourse(true);
      try {
        const response = await fetchCourseDetailRequest(courseId, token);
        if (isMounted) {
          setCourse(response);
          setLoadError("");
        }
      } catch (error) {
        if (isMounted) {
          setCourse({
            id: courseId,
            title: "",
            progress: { completionPercentage: 0 },
            contentItems: [],
          });
          setLoadError(error.message || "Live lesson data could not be loaded.");
        }
      } finally {
        if (isMounted) {
          setIsLoadingCourse(false);
        }
      }
    };

    if (token) {
      loadCourse();
    }

    return () => {
      isMounted = false;
    };
  }, [courseId, token]);

  useEffect(() => {
    let isMounted = true;

    const loadContent = async () => {
      try {
        const response = await fetchCourseContentRequest(courseId, contentId, token);
        if (isMounted) {
          setContentOverride(response.contentItem);
          setContentAccessError("");
          setQuizError("");
        }
      } catch (error) {
        if (isMounted) {
          setContentOverride(null);
          setContentAccessError(error.message || "This learning content is currently unavailable.");
        }
      }
    };

    if (token && contentId) {
      loadContent();
    }

    return () => {
      isMounted = false;
    };
  }, [contentId, courseId, token]);

  const contentItem = course.contentItems.find((item) => item.id === contentId) ?? null;
  const resolvedContentItem = contentOverride?.id === contentId
    ? contentItem
      ? {
        ...contentItem,
        ...contentOverride,
      }
      : contentOverride
    : contentItem;

  const handleSelectQuizOption = (questionId, optionIndex) => {
    setQuizSelections((current) => ({
      ...current,
      [questionId]: (() => {
        const currentSelections = current[questionId] ?? [];
        const allowsMultipleAnswers = resolvedContentItem?.quizQuestions?.find(
          (question) => question.id === questionId,
        )?.allowsMultipleAnswers;

        if (!allowsMultipleAnswers) {
          return [optionIndex];
        }

        return currentSelections.includes(optionIndex)
          ? currentSelections.filter((value) => value !== optionIndex)
          : [...currentSelections, optionIndex].sort((left, right) => left - right);
      })(),
    }));
  };

  const handleSubmitQuizAttempt = async ({ isFinalQuestion, questionNumber }) => {
    if (!resolvedContentItem?.quizQuestions) {
      return;
    }

    if (!isFinalQuestion) {
      navigate(
        buildQuizQuestionRoute(course.id, resolvedContentItem.id, questionNumber + 1),
      );
      return;
    }

    setIsSubmittingQuiz(true);
    setQuizError("");

    try {
      const response = await submitQuizAttemptRequest(course.id, resolvedContentItem.id, token, {
        answers: resolvedContentItem.quizQuestions.map((question) => ({
          questionId: question.id,
          selectedOptionIndexes: quizSelections[question.id] ?? [],
        })),
      });

      setQuizReward(response);

      const refreshedCourse = await fetchCourseDetailRequest(course.id, token);
      setCourse(refreshedCourse);
      navigate(buildQuizRewardRoute(course.id, resolvedContentItem.id));
    } catch (error) {
      setQuizError(error.message || "Quiz submission could not be completed.");
    } finally {
      setIsSubmittingQuiz(false);
    }
  };

  const handleAdvanceContent = async () => {
    if (!resolvedContentItem) {
      navigate(`/courses/${course.id}`);
      return;
    }

    try {
      if (resolvedContentItem.mode !== LEARNING_CONTENT_MODE.QUIZ && token) {
        await updateCourseContentProgressRequest(course.id, resolvedContentItem.id, token, {
          status: "completed",
          lastPosition: 100,
        });
      }

      const refreshedCourse = token ? await fetchCourseDetailRequest(course.id, token) : course;
      setCourse(refreshedCourse);
      const nextContent = resolvedContentItem.nextContentId
        ? refreshedCourse.contentItems.find((item) => item.id === resolvedContentItem.nextContentId)
        : null;

      if (nextContent && !nextContent.isLocked) {
        navigate(buildLearningRoute(course.id, nextContent));
        return;
      }

      navigate(`/courses/${course.id}`);
    } catch (error) {
      setQuizError(error.message || "Could not move to the next content item.");
    }
  };

  useEffect(() => {
    if (!resolvedContentItem || !mode) {
      return;
    }

    if (
      resolvedContentItem.mode !== mode &&
      !(mode === LEARNING_CONTENT_MODE.QUIZ && resolvedContentItem.mode === LEARNING_CONTENT_MODE.QUIZ)
    ) {
      navigate(buildLearningRoute(course.id, resolvedContentItem), { replace: true });
    }
  }, [resolvedContentItem, course.id, mode, navigate]);

  if (!resolvedContentItem) {
    return null;
  }

  return (
    <main className="learning-page-shell">
      <div className={`learning-player-frame ${isSidebarOpen ? "" : "is-sidebar-collapsed"}`}>
        <LearningSidebar
          course={course}
          currentContentId={resolvedContentItem?.id ?? contentId}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen((current) => !current)}
        />
        <section className="learning-main-panel">
          <StatusBanner
            tone={loadError ? "error" : "info"}
            message={loadError}
            onClose={() => setLoadError("")}
          />
          <StatusBanner
            tone="error"
            message={quizError}
            onClose={() => setQuizError("")}
          />
          <StatusBanner
            tone="error"
            message={contentAccessError}
            onClose={() => setContentAccessError("")}
          />
          {isLoadingCourse ? (
            <LoadingBlock
              title="Loading learning player"
              description="Preparing your content, progress, and lesson outline."
            />
          ) : contentAccessError ? (
            <EmptyState
              title="This content is locked"
              description={contentAccessError}
              action={
                <Link className="catalog-action-button instructor-cta-button" to={`/courses/${course.id}`}>
                  Back to Course
                </Link>
              }
            />
          ) : resolvedContentItem ? (
          <LearningMainContent
            key={`${resolvedContentItem.id}:${location.pathname}`}
            course={course}
            contentItem={resolvedContentItem}
            questionIndex={questionIndex ?? null}
            pathname={location.pathname}
            quizSelections={quizSelections}
            onSelectQuizOption={handleSelectQuizOption}
            onSubmitQuizAttempt={handleSubmitQuizAttempt}
            quizReward={quizReward}
            isSubmittingQuiz={isSubmittingQuiz}
            onCloseReward={() => navigate(`/courses/${course.id}`)}
            onAdvanceContent={handleAdvanceContent}
          />
          ) : (
            <EmptyState
              title="This content is unavailable"
              description="The selected lesson could not be resolved. Return to the course page and choose another item."
              action={
                <Link className="catalog-action-button instructor-cta-button" to={`/courses/${course.id}`}>
                  Back to Course
                </Link>
              }
            />
          )}
        </section>
      </div>
    </main>
  );
}
