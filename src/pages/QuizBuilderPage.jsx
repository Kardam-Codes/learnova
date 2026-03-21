/*
 * File: QuizBuilderPage.jsx
 * Owner: YUG
 * Purpose: Render the instructor quiz builder with question editing and reward configuration.
 * What it is: A route-level page that matches the split-pane quiz builder layout from the reference screenshots.
 */
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import InstructorNavbar from "../components/InstructorNavbar";
import { quizBuilderMock } from "../data/instructorMock";

function QuestionEditor({ questionIndex, question }) {
  return (
    <>
      <div className="quiz-editor-heading quiz-editor-heading-annotated">
        <strong>{questionIndex + 1}.</strong>
        <input type="text" defaultValue={question.prompt} />
      </div>

      <div className="quiz-choice-header quiz-choice-header-annotated">
        <span>Choices</span>
        <span>Correct</span>
      </div>

      <div className="quiz-choice-list quiz-choice-list-annotated">
        {question.choices.map((choice) => (
          <label key={choice.id} className="quiz-choice-row quiz-choice-row-annotated">
            <span>{choice.label}</span>
            <input type="checkbox" defaultChecked={choice.isCorrect} />
          </label>
        ))}
      </div>

      <button type="button" className="quiz-add-choice-link quiz-add-choice-link-annotated">
        Add choice
      </button>
    </>
  );
}

function RewardsEditor({ rewards }) {
  return (
    <div className="quiz-rewards-panel quiz-rewards-panel-annotated quiz-rewards-panel-compact">
      <h2>Rewards</h2>
      <div className="reward-line reward-line-annotated">
        <span>First try :</span>
        <input type="text" defaultValue={rewards.first} />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated">
        <span>Second try :</span>
        <input type="text" defaultValue={rewards.second} />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated">
        <span>Third try :</span>
        <input type="text" defaultValue={rewards.third} />
        <span>points</span>
      </div>
      <div className="reward-line reward-line-annotated reward-line-long-label">
        <span>Fourth Try and more :</span>
        <input type="text" defaultValue={rewards.fourthPlus} />
        <span>points</span>
      </div>
    </div>
  );
}

export default function QuizBuilderPage() {
  const { quizId } = useParams();
  const quiz = useMemo(() => quizBuilderMock, [quizId]);
  const [panelMode, setPanelMode] = useState("question");
  const [selectedQuestionId, setSelectedQuestionId] = useState(quiz.questions[0].id);

  const selectedQuestion =
    quiz.questions.find((question) => question.id === selectedQuestionId) ??
    quiz.questions[0];
  const selectedQuestionIndex = quiz.questions.findIndex(
    (question) => question.id === selectedQuestion.id,
  );

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="quiz-builder-shell quiz-builder-shell-annotated">
          <aside className="quiz-builder-sidebar quiz-builder-sidebar-annotated">
            <h2>Question List</h2>

            <div className="quiz-question-list">
              {quiz.questions.map((question, index) => (
                <button
                  key={question.id}
                  type="button"
                  className={`quiz-list-item${
                    selectedQuestion.id === question.id && panelMode === "question"
                      ? " is-active"
                      : ""
                  }`}
                  onClick={() => {
                    setSelectedQuestionId(question.id);
                    setPanelMode("question");
                  }}
                >
                  Question {index + 1}
                </button>
              ))}
            </div>

            <button type="button" className="catalog-action-button instructor-cta-button quiz-sidebar-button">
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
            {panelMode === "question" ? (
              <QuestionEditor questionIndex={selectedQuestionIndex} question={selectedQuestion} />
            ) : (
              <RewardsEditor rewards={quiz.rewards} />
            )}
          </section>
        </section>
      </div>
    </main>
  );
}
