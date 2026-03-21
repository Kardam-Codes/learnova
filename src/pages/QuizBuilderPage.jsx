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

export default function QuizBuilderPage() {
  const { quizId } = useParams();
  const quiz = useMemo(() => quizBuilderMock, [quizId]);
  const [panelMode, setPanelMode] = useState("question");
  const [selectedQuestionId, setSelectedQuestionId] = useState(quiz.questions[0].id);

  const selectedQuestion =
    quiz.questions.find((question) => question.id === selectedQuestionId) ??
    quiz.questions[0];

  return (
    <main className="course-page-shell instructor-page-shell">
      <InstructorNavbar />

      <div className="course-page-card instructor-shell">
        <section className="quiz-builder-shell">
          <aside className="quiz-builder-sidebar">
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

          <section className="quiz-builder-panel">
            {panelMode === "question" ? (
              <>
                <div className="quiz-editor-heading">
                  <strong>{quiz.questions.findIndex((item) => item.id === selectedQuestion.id) + 1}.</strong>
                  <input type="text" defaultValue={selectedQuestion.prompt} />
                </div>

                <div className="quiz-choice-header">
                  <span>Choices</span>
                  <span>Correct</span>
                </div>

                <div className="quiz-choice-list">
                  {selectedQuestion.choices.map((choice) => (
                    <label key={choice.id} className="quiz-choice-row">
                      <span>{choice.label}</span>
                      <input type="checkbox" defaultChecked={choice.isCorrect} />
                    </label>
                  ))}
                </div>

                <button type="button" className="quiz-add-choice-link">
                  Add choice
                </button>
              </>
            ) : (
              <div className="quiz-rewards-panel quiz-rewards-panel-annotated">
                <h2>Rewards</h2>
                <div className="reward-line reward-line-annotated">
                  <span>First try :</span>
                  <input type="text" defaultValue={quiz.rewards.first} />
                  <span>points</span>
                </div>
                <div className="reward-line reward-line-annotated">
                  <span>Second try :</span>
                  <input type="text" defaultValue={quiz.rewards.second} />
                  <span>points</span>
                </div>
                <div className="reward-line reward-line-annotated">
                  <span>Third try :</span>
                  <input type="text" defaultValue={quiz.rewards.third} />
                  <span>points</span>
                </div>
                <div className="reward-line reward-line-annotated reward-line-long-label">
                  <span>Fourth Try and more :</span>
                  <input type="text" defaultValue={quiz.rewards.fourthPlus} />
                  <span>points</span>
                </div>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}
