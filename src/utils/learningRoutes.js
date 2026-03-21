/*
 * File: learningRoutes.js
 * Owner: KARDAM
 * Purpose: Centralize learner route generation for document, video, and quiz states.
 * What it is: Small helpers that keep dashboard, detail, and player navigation consistent.
 */
import { LEARNING_CONTENT_MODE } from "../../shared/types/common_types";

export function buildLearningRoute(courseId, contentItem) {
  return `/courses/${courseId}/learn/${contentItem.id}/${contentItem.mode}`;
}

export function buildQuizQuestionRoute(courseId, contentId, questionIndex) {
  return `/courses/${courseId}/learn/${contentId}/${LEARNING_CONTENT_MODE.QUIZ}/question/${questionIndex}`;
}

export function buildQuizRewardRoute(courseId, contentId) {
  return `/courses/${courseId}/learn/${contentId}/${LEARNING_CONTENT_MODE.QUIZ}/reward`;
}
