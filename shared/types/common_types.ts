/*
 * File: common_types.ts
 * Owner: BOTH CAN ADD
 * Purpose: Store shared frontend constants and data-shape notes used across learner pages.
 * What it is: A lightweight shared contract file for course, content, and profile view models.
 */
export const COURSE_CONTENT_STATUS = {
  NOT_STARTED: "not_started",
  IN_PROGRESS: "in_progress",
  COMPLETED: "completed",
};

export const COURSE_CONTENT_TYPE = {
  LESSON: "lesson",
  QUIZ: "quiz",
};

export const COURSE_ACCESS_STATE = {
  JOIN: "join",
  START: "start",
  CONTINUE: "continue",
  BUY: "buy",
};

export const PROFILE_BADGE_LEVEL = {
  NEWBIE: "Newbie",
  EXPLORER: "Explorer",
  ACHIEVER: "Achiever",
  SPECIALIST: "Specialist",
  EXPERT: "Expert",
  MASTER: "Master",
};

/**
 * @typedef {"not_started" | "in_progress" | "completed"} CourseContentStatus
 * @typedef {"lesson" | "quiz"} CourseContentType
 * @typedef {"join" | "start" | "continue" | "buy"} CourseAccessState
 *
 * @typedef {Object} CourseProgressSummary
 * @property {number} completionPercentage
 * @property {number} totalCount
 * @property {number} completedCount
 * @property {number} incompleteCount
 *
 * @typedef {Object} CourseContentItem
 * @property {string} id
 * @property {string} title
 * @property {CourseContentType} type
 * @property {CourseContentStatus} status
 * @property {number} order
 * @property {string} [description]
 * @property {string} [duration]
 *
 * @typedef {Object} CourseDetailViewModel
 * @property {string} id
 * @property {string} title
 * @property {string} shortDescription
 * @property {string} thumbnail
 * @property {string} coverImage
 * @property {string} providerName
 * @property {string} learnerName
 * @property {CourseProgressSummary} progress
 * @property {CourseContentItem[]} contentItems
 *
 * @typedef {Object} CourseCatalogItem
 * @property {string} id
 * @property {string} title
 * @property {string} shortDescription
 * @property {string} coverImage
 * @property {string[]} tags
 * @property {boolean} isPaid
 * @property {number | null} price
 * @property {boolean} isPurchased
 * @property {boolean} isLoggedIn
 * @property {boolean} hasStarted
 * @property {boolean} isInProgress
 * @property {string} detailPath
 * @property {string} firstContentId
 * @property {string} lastContentId
 *
 * @typedef {Object} LearnerBadgeTier
 * @property {string} name
 * @property {number} minPoints
 * @property {number} maxPoints
 *
 * @typedef {Object} LearnerProfileViewModel
 * @property {string} learnerName
 * @property {number} totalPoints
 * @property {string} currentBadge
 * @property {LearnerBadgeTier[]} badgeTiers
 */
