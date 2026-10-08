/*
 * File: QuizBuilderPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor quiz builder with question editing and reward configuration.
 * What it is: A route-level page that uses the live admin quiz CRUD APIs while preserving the split-pane builder layout.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import InstructorNavbar from "../components/InstructorNavbar";
import LoadingBlock from "../components/LoadingBlock";
import StatusBanner from "../components/StatusBanner";
import { quizBuilderMock } from "../data/instructorMock";
import { useAuth } from "../context/AuthContext";
import {
  createAdminQuizRequest,
  deleteAdminQuizRequest,
  fetchAdminQuizRequest,
  updateAdminQuizRequest,
} from "../utils/apiClient";

function buildQuestionChoice(label = "", isCorrect = false) {
  return {
    id: crypto.randomUUID(),
    label,
    isCorrect,
  };
}

function buildQuestion(prompt = "Write your question here") {
  return {
    id: crypto.randomUUID(),
    prompt,
    choices: [
      buildQuestionChoice("Answer 1", true),
      buildQuestionChoice("Answer 2", false),
      buildQuestionChoice("Answer 3", false),
      buildQuestionChoice("Answer 4", false),
    ],
  };
}

function buildInitialQuizState() {
  return {
    id: "new-quiz",
    title: "",
    courseSlug: "",
    contentSlug: "",
    description: "",
    durationLabel: "3 questions",
    maxAttempts: 4,
    rewards: {
      first: 10,
      second: 7,
      third: 5,
      fourthPlus: 2,
    },
    questions: [buildQuestion()],
  };
}

function QuestionEditor({
  questionIndex,
  question,
  onPromptChange,
  onChoiceLabelChange,
  onChoiceCorrectChange,
  onDeleteChoice,
  onAddChoice,
}) {
  return (
    <>
      <div className="quiz-editor-eyebrow">Question editor</div>
      <div className="quiz-editor-heading quiz-editor-heading-annotated">
        <strong>{questionIndex + 1}.</strong>
        <input
          type="text"
          className="quiz-prompt-input"
          value={question.prompt}
          onChange={(event) => onPromptChange(event.target.value)}
        />
      </div>
      <p className="quiz-editor-helper">
        Keep the prompt concise and make the choices clearly distinguishable for learners.
      </p>

      <div className="quiz-choice-header quiz-choice-header-annotated">
        <span>Choices</span>
        <span>Correct</span>
      </div>

      <div className="quiz-choice-list quiz-choice-list-annotated">
        {question.choices.map((choice, choiceIndex) => (
          <div key={choice.id} className="quiz-choice-row quiz-choice-row-annotated">
            <div className="quiz-choice-copy">
              <span className="quiz-choice-index">Choice {choiceIndex + 1}</span>
              <input
                type="text"
                value={choice.label}
                onChange={(event) => onChoiceLabelChange(choice.id, event.target.value)}
              />
            </div>
            <div className="quiz-choice-actions">
              <input
                type="checkbox"
                checked={choice.isCorrect}
                onChange={(event) => onChoiceCorrectChange(choice.id, event.target.checked)}
              />
              <button
                type="button"
                className="quiz-choice-delete-button"
                onClick={() => onDeleteChoice(choice.id)}
                disabled={question.choices.length <= 2}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      <button type="button" className="quiz-add-choice-link quiz-add-choice-link-annotated" onClick={onAddChoice}>
        Add choice
      </button>
    </>
  );
}

function RewardsEditor({ rewards, maxAttempts, onRewardChange, onMaxAttemptsChange }) {
  return (
    <div className="quiz-rewards-panel quiz-rewards-panel-annotated quiz-rewards-panel-compact">
      <h2>Rewards</h2>
      <p className="quiz-editor-helper">
        Learners earn fewer points with later attempts, so use this section to reinforce mastery on the first try.
      </p>
      <label className="reward-line reward-line-annotated reward-line-long-label">
        <span>Maximum attempts :</span>
        <input
          type="number"
          min="1"
          value={maxAttempts}
          onChange={(event) => onMaxAttemptsChange(event.target.value)}
        />
        <span>times</span>
      </label>
      <div className="reward-line reward-line-annotated">
        <span>First try :</span>
        <input
          type="number"
          value={rewards.first}
          onChange={(event) => onRewardChange("first", event.target.value)}
        />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated">
        <span>Second try :</span>
        <input
          type="number"
          value={rewards.second}
          onChange={(event) => onRewardChange("second", event.target.value)}
        />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated">
        <span>Third try :</span>
        <input
          type="number"
          value={rewards.third}
          onChange={(event) => onRewardChange("third", event.target.value)}
        />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated reward-line-long-label">
        <span>Fourth Try and more :</span>
        <input
          type="number"
          value={rewards.fourthPlus}
          onChange={(event) => onRewardChange("fourthPlus", event.target.value)}
        />
        <span>points</span>
      </div>
    </div>
  );
}

function mapQuizFromApi(quiz) {
  return {
    id: quiz.id,
    title: quiz.title ?? "",
    courseSlug: quiz.courseSlug ?? "",
    contentSlug: quiz.contentSlug ?? "",
    description: quiz.description ?? "",
    durationLabel: quiz.durationLabel ?? "",
    maxAttempts: quiz.maxAttempts ?? 4,
    rewards: {
      first: quiz.rewards?.first ?? 0,
      second: quiz.rewards?.second ?? 0,
      third: quiz.rewards?.third ?? 0,
      fourthPlus: quiz.rewards?.fourthPlus ?? 0,
    },
    questions:
      quiz.questions?.map((question) => ({
        id: question.id,
        prompt: question.prompt,
        choices: question.choices.map((choice) => ({
          id: choice.id,
          label: choice.label,
          isCorrect: Boolean(choice.isCorrect),
        })),
      })) ?? [buildQuestion()],
  };
}

export default function QuizBuilderPage({ theme, toggleTheme }) {
  const { quizId = "new-quiz" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const courseSlug = searchParams.get("course") ?? "odoo-crm";
  const fallbackQuiz = useMemo(() => mapQuizFromApi(quizBuilderMock), []);
  const [quiz, setQuiz] = useState(() => buildInitialQuizState());
  const [panelMode, setPanelMode] = useState("question");
  const [selectedQuestionId, setSelectedQuestionId] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const isNewQuiz = quizId === "new-quiz";

  useEffect(() => {
    let isMounted = true;

    const loadQuiz = async () => {
      setIsLoading(true);
      if (isNewQuiz) {
        const nextQuiz = {
          ...buildInitialQuizState(),
          courseSlug,
        };
        setQuiz(nextQuiz);
        setSelectedQuestionId(nextQuiz.questions[0].id);
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetchAdminQuizRequest(quizId, token);
        if (!isMounted) {
          return;
        }

        const nextQuiz = mapQuizFromApi(response);
        setQuiz(nextQuiz);
        setSelectedQuestionId(nextQuiz.questions[0]?.id ?? "");
        setStatusMessage("");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setQuiz(fallbackQuiz);
        setSelectedQuestionId(fallbackQuiz.questions[0]?.id ?? "");
        setStatusMessage(error.message);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    if (token) {
      loadQuiz();
    }

    return () => {
      isMounted = false;
    };
  }, [courseSlug, fallbackQuiz, isNewQuiz, quizId, token]);

  const selectedQuestion =
    quiz.questions.find((question) => question.id === selectedQuestionId) ??
    quiz.questions[0];
  const selectedQuestionIndex = quiz.questions.findIndex(
    (question) => question.id === selectedQuestion?.id,
  );

  const updateQuestion = (questionId, updater) => {
    setQuiz((current) => ({
      ...current,
      questions: current.questions.map((question) =>
        question.id === questionId ? updater(question) : question,
      ),
    }));
  };

  const handleAddQuestion = () => {
    const newQuestion = buildQuestion();
    setQuiz((current) => ({
      ...current,
      questions: [...current.questions, newQuestion],
      durationLabel: `${current.questions.length + 1} questions`,
    }));
    setSelectedQuestionId(newQuestion.id);
    setPanelMode("question");
  };

  const handleAddChoice = () => {
    if (!selectedQuestion) {
      return;
    }

    updateQuestion(selectedQuestion.id, (question) => ({
      ...question,
      choices: [...question.choices, buildQuestionChoice(`Answer ${question.choices.length + 1}`, false)],
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setStatusMessage("");

    const payload = {
      title: quiz.title,
      description: quiz.description,
      durationLabel: quiz.durationLabel || `${quiz.questions.length} questions`,
      maxAttempts: Number(quiz.maxAttempts) || 1,
      questions: quiz.questions.map((question) => ({
        prompt: question.prompt,
        choices: question.choices.map((choice) => ({
          label: choice.label,
          isCorrect: choice.isCorrect,
        })),
      })),
      rewards: {
        first: Number(quiz.rewards.first) || 0,
        second: Number(quiz.rewards.second) || 0,
        third: Number(quiz.rewards.third) || 0,
        fourthPlus: Number(quiz.rewards.fourthPlus) || 0,
      },
    };

    try {
      const response = isNewQuiz
        ? await createAdminQuizRequest(courseSlug, token, payload)
        : await updateAdminQuizRequest(quiz.id, token, payload);

      const nextQuiz = mapQuizFromApi(response);
      setQuiz(nextQuiz);
      setSelectedQuestionId(nextQuiz.questions[0]?.id ?? "");
      setStatusMessage("Quiz saved successfully.");

      if (isNewQuiz) {
        navigate(`/instructor/quizzes/${response.id}/builder?course=${response.courseSlug}`, {
          replace: true,
        });
      }
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (isNewQuiz) {
      navigate(`/instructor/courses/${courseSlug}/edit`);
      return;
    }

    setIsDeleting(true);
    try {
      await deleteAdminQuizRequest(quiz.id, token);
      navigate(`/instructor/courses/${quiz.courseSlug || courseSlug}/edit`);
    } catch (error) {
      setStatusMessage(error.message);
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleDeleteChoice = (choiceId) => {
    if (!selectedQuestion || selectedQuestion.choices.length <= 2) {
      return;
    }

    updateQuestion(selectedQuestion.id, (question) => ({
      ...question,
      choices: question.choices.filter((choice) => choice.id !== choiceId),
    }));
  };

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar theme={theme} toggleTheme={toggleTheme} />

      <div className="course-page-card instructor-shell">
        <section className="quiz-builder-shell quiz-builder-shell-annotated">
          <aside className="quiz-builder-sidebar quiz-builder-sidebar-annotated">
            <div className="quiz-builder-sidebar-header">
              <div className="quiz-builder-sidebar-topline">
                <Link
                  to={`/instructor/courses/${quiz.courseSlug || courseSlug}/edit`}
                  className="quiz-builder-back-link"
                  aria-label="Back to course"
                >
                  <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
                    <path d="M14.5 5 7.5 12l7 7" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M8.5 12h9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </Link>
                <span className="eyebrow">Quiz Builder</span>
              </div>
              <h2>Structure the assessment</h2>
            </div>
            <div className="quiz-builder-stats">
              <span className="quiz-builder-stat">
                <strong>{quiz.questions.length}</strong>
                <span>Questions</span>
              </span>
              <span className="quiz-builder-stat">
                <strong>{quiz.maxAttempts}</strong>
                <span>Attempts</span>
              </span>
            </div>

            <label className="editor-line-field editor-line-field-wide">
              <span>Quiz Title:</span>
              <input
                type="text"
                value={quiz.title}
                onChange={(event) =>
                  setQuiz((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
              />
            </label>

            <label className="editor-line-field editor-line-field-wide">
              <span>Description:</span>
              <input
                type="text"
                className="quiz-description-input"
                value={quiz.description}
                onChange={(event) =>
                  setQuiz((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
            <p className="quiz-sidebar-helper">This description is shown to learners before they begin the quiz.</p>

            <h2>Question List</h2>

            <div className="quiz-question-list">
              {quiz.questions.map((question, index) => (
                <button
                  key={question.id}
                  type="button"
                  className={`quiz-list-item${
                    selectedQuestion?.id === question.id && panelMode === "question"
                      ? " is-active"
                      : ""
                  }`}
                  onClick={() => {
                    setSelectedQuestionId(question.id);
                    setPanelMode("question");
                  }}
                >
                  <span>Question {index + 1}</span>
                  <small>{question.choices.length} choices</small>
                </button>
              ))}
            </div>

            <button type="button" className="catalog-action-button instructor-cta-button quiz-sidebar-button" onClick={handleAddQuestion}>
              Add Question
            </button>

            <button
              type="button"
              className={`catalog-action-button instructor-cta-button quiz-sidebar-button${
                panelMode === "rewards" ? " is-active" : ""
              }`}
              onClick={() => setPanelMode("rewards")}
            >
              Rewards
            </button>
          </aside>

          <section className="quiz-builder-panel quiz-builder-panel-annotated">
            <div className="quiz-builder-panel-header">
              <span className="eyebrow">{panelMode === "rewards" ? "Rewards" : "Question Workspace"}</span>
              <h2>{panelMode === "rewards" ? "Tune scoring by attempt" : `Editing ${selectedQuestion ? `Question ${selectedQuestionIndex + 1}` : "Question"}`}</h2>
            </div>
            <div className="inline-button-row instructor-top-right">
              <button
                type="button"
                className="catalog-action-button instructor-ghost-button"
                onClick={() => setShowDeleteDialog(true)}
              >
                Delete
              </button>
              <button
                type="button"
                className="catalog-action-button instructor-cta-button"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save Quiz"}
              </button>
            </div>

            <StatusBanner
              tone={
                statusMessage?.toLowerCase().includes("successfully")
                  ? "success"
                  : statusMessage?.toLowerCase().includes("not")
                    ? "error"
                    : "info"
              }
              message={statusMessage}
              onClose={() => setStatusMessage("")}
            />

            {isLoading ? (
              <LoadingBlock
                title="Loading quiz builder"
                description="Preparing questions, rewards, and quiz settings."
              />
            ) : null}

            {!isLoading && panelMode === "question" && selectedQuestion ? (
              <QuestionEditor
                questionIndex={selectedQuestionIndex}
                question={selectedQuestion}
                onPromptChange={(value) =>
                  updateQuestion(selectedQuestion.id, (question) => ({
                    ...question,
                    prompt: value,
                  }))
                }
                onChoiceLabelChange={(choiceId, value) =>
                  updateQuestion(selectedQuestion.id, (question) => ({
                    ...question,
                    choices: question.choices.map((choice) =>
                      choice.id === choiceId ? { ...choice, label: value } : choice,
                    ),
                  }))
                }
                onChoiceCorrectChange={(choiceId, checked) =>
                  updateQuestion(selectedQuestion.id, (question) => ({
                    ...question,
                    choices: question.choices.map((choice) =>
                      choice.id === choiceId ? { ...choice, isCorrect: checked } : choice,
                    ),
                  }))
                }
                onDeleteChoice={handleDeleteChoice}
                onAddChoice={handleAddChoice}
              />
            ) : null}

            {!isLoading && panelMode === "rewards" ? (
              <RewardsEditor
                rewards={quiz.rewards}
                maxAttempts={quiz.maxAttempts}
                onRewardChange={(field, value) =>
                  setQuiz((current) => ({
                    ...current,
                    rewards: {
                      ...current.rewards,
                      [field]: value,
                    },
                  }))
                }
                onMaxAttemptsChange={(value) =>
                  setQuiz((current) => ({
                    ...current,
                    maxAttempts: value,
                  }))
                }
              />
            ) : null}
          </section>
        </section>
      </div>
      {showDeleteDialog ? (
        <ConfirmDialog
          title="Delete quiz"
          description="This quiz will be removed from the course and learners will no longer be able to attempt it."
          confirmLabel="Delete quiz"
          isSubmitting={isDeleting}
          onConfirm={handleDelete}
          onClose={() => setShowDeleteDialog(false)}
        />
      ) : null}
    </main>
  );
}
