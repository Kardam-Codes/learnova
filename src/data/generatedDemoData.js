/*
 * File: generatedDemoData.js
 * Purpose: Provide large generated fallback data for learner catalog and reporting screens.
 * What it is: Deterministic demo-data builders used when the live backend is empty or unavailable.
 */

import {
  COURSE_CONTENT_STATUS,
  COURSE_CONTENT_TYPE,
  LEARNING_CONTENT_MODE,
} from "../../shared/types/common_types";

const COURSE_TARGET = 200;
const REPORT_TARGET = 320;
const PDF_URL = "/docs/dummy.pdf";

function pad(value) {
  return String(value).padStart(3, "0");
}

function createCourseCard(index) {
  const id = `bulk-course-${pad(index)}`;
  const isPaid = index % 4 === 0;
  const isEnrolled = index <= 24;
  const isInProgress = index <= 12;

  return {
    id,
    title: `Bulk Course ${pad(index)}`,
    shortDescription: `Generated learner catalog course ${pad(index)} with videos, documents, and quiz practice.`,
    coverImage: `https://picsum.photos/seed/${id}/600/400`,
    tags: [`Track ${((index - 1) % 8) + 1}`, index % 2 === 0 ? "Automation" : "Analytics", index % 3 === 0 ? "Advanced" : "Beginner"],
    isPaid,
    price: isPaid ? 499 + index : null,
    accessRule: isPaid ? "payment" : "open",
    paymentStatus: isPaid ? (isEnrolled ? "paid" : "pending") : "not_required",
    isPurchased: isPaid ? isEnrolled : true,
    isEnrolled,
    isLoggedIn: true,
    hasStarted: isInProgress,
    isInProgress,
    detailPath: `/courses/${id}`,
    firstContentId: `${id}-video`,
    firstContentMode: LEARNING_CONTENT_MODE.VIDEO,
    lastContentId: isInProgress ? `${id}-document` : `${id}-video`,
    lastContentMode: isInProgress ? LEARNING_CONTENT_MODE.DOCUMENT : LEARNING_CONTENT_MODE.VIDEO,
  };
}

function createContentItems(courseId) {
  return [
    {
      id: `${courseId}-video`,
      title: "Video Lesson",
      type: COURSE_CONTENT_TYPE.LESSON,
      mode: LEARNING_CONTENT_MODE.VIDEO,
      status: COURSE_CONTENT_STATUS.COMPLETED,
      order: 1,
      duration: "12 min",
      description: "Generated demo video lesson.",
      contentUrl: "https://www.youtube.com/embed/ysz5S6PUM-U",
      attachments: [],
      nextContentId: `${courseId}-document`,
    },
    {
      id: `${courseId}-document`,
      title: "Workbook",
      type: COURSE_CONTENT_TYPE.LESSON,
      mode: LEARNING_CONTENT_MODE.DOCUMENT,
      status: COURSE_CONTENT_STATUS.IN_PROGRESS,
      order: 2,
      duration: "10 min",
      description: "Generated demo workbook lesson.",
      contentUrl: PDF_URL,
      attachments: [
        {
          id: `${courseId}-attachment`,
          label: "Workbook PDF",
          url: "https://example.com/generated-workbook.pdf",
        },
      ],
      nextContentId: `${courseId}-quiz`,
    },
    {
      id: `${courseId}-quiz`,
      title: "Knowledge Check",
      type: COURSE_CONTENT_TYPE.QUIZ,
      mode: LEARNING_CONTENT_MODE.QUIZ,
      status: COURSE_CONTENT_STATUS.NOT_STARTED,
      order: 3,
      duration: "3 questions",
      description: "Generated quiz content for bulk demo browsing.",
      nextContentId: null,
      quizRules: {
        totalQuestions: 2,
        maxAttempts: 3,
      },
      quizQuestions: [
        {
          id: `${courseId}-q1`,
          prompt: "Which action usually helps learners complete a course?",
          options: ["Clear lesson flow", "No guidance", "Hidden progress"],
          allowsMultipleAnswers: false,
        },
        {
          id: `${courseId}-q2`,
          prompt: "Which items can be useful in a structured learning path?",
          options: ["Video lesson", "Workbook", "Quiz"],
          allowsMultipleAnswers: true,
        },
      ],
      reward: {
        pointsEarned: 15,
        nextTarget: 100,
        message: "Generated reward preview for demo browsing.",
      },
    },
  ];
}

export function buildGeneratedCatalogData(learnerName = "Learner") {
  const courses = Array.from({ length: COURSE_TARGET }, (_, index) => createCourseCard(index + 1));
  return {
    profile: {
      learnerName,
      totalPoints: 84,
      currentBadge: "Expert",
      badgeTiers: [],
    },
    courses: courses.filter((course) => course.isEnrolled),
    enrolledCourses: courses.filter((course) => course.isEnrolled),
    availableCourses: courses.filter((course) => !course.isEnrolled),
  };
}

export function getGeneratedCourseDetail(courseId, learnerName = "Learner") {
  if (!/^bulk-course-\d{3}$/.test(courseId)) {
    return null;
  }

  const index = Number(courseId.slice(-3));
  const card = createCourseCard(index);

  return {
    id: courseId,
    title: card.title,
    shortDescription: card.shortDescription,
    thumbnail: card.coverImage,
    coverImage: card.coverImage,
    providerName: "Learnova",
    learnerName,
    isEnrolled: card.isEnrolled,
    paymentStatus: card.paymentStatus,
    accessRule: card.accessRule,
    canEnrollFree: !card.isPaid && !card.isEnrolled,
    requiresPayment: card.isPaid && !card.isEnrolled,
    price: card.price,
    progress: {
      completionPercentage: card.isInProgress ? 33 : 0,
      totalCount: 3,
      completedCount: card.isInProgress ? 1 : 0,
      incompleteCount: card.isInProgress ? 2 : 3,
    },
    contentItems: createContentItems(courseId),
    reviews: {
      averageRating: 4.4,
      totalReviews: 2,
      items: [
        {
          id: `${courseId}-review-1`,
          authorName: "Generated Learner 1",
          rating: 5,
          comment: "Helpful structure and a clean generated content path.",
        },
        {
          id: `${courseId}-review-2`,
          authorName: "Generated Learner 2",
          rating: 4,
          comment: "Useful for testing large catalog views.",
        },
      ],
      learnerDraft: "Generated review draft.",
    },
  };
}

function createReportRow(index) {
  const courseIndex = ((index - 1) % 40) + 1;
  const statusCycle = index % 3;
  const status = statusCycle === 0 ? "completed" : statusCycle === 1 ? "in_progress" : "yet_to_start";
  return {
    id: index,
    courseId: `bulk-report-course-${String(courseIndex).padStart(2, "0")}`,
    courseName: `Reporting Course ${String(courseIndex).padStart(2, "0")}`,
    participantId: `bulk-report-user-${pad(index)}`,
    participantName: `Generated Participant ${pad(index)}`,
    enrolledDate: `2026-02-${String((index % 27) + 1).padStart(2, "0")}T00:00:00.000Z`,
    startDate: status === "yet_to_start" ? null : `2026-03-${String((index % 20) + 1).padStart(2, "0")}T00:00:00.000Z`,
    timeSpent: status === "completed" ? "25:40" : status === "in_progress" ? "8:15" : "0:00",
    completionPercentage: status === "completed" ? "100%" : status === "in_progress" ? "33%" : "0%",
    completedDate: status === "completed" ? `2026-03-${String((index % 20) + 1).padStart(2, "0")}T00:00:00.000Z` : null,
    status,
  };
}

export function buildGeneratedReportingData(rowCount = REPORT_TARGET) {
  const rows = Array.from({ length: rowCount }, (_, index) => createReportRow(index + 1));
  const summary = [
    { id: "participants", label: "Total Participants", value: rows.length },
    { id: "yet-to-start", label: "Yet to Start", value: rows.filter((row) => row.status === "yet_to_start").length },
    { id: "in-progress", label: "In Progress", value: rows.filter((row) => row.status === "in_progress").length },
    { id: "completed", label: "Completed", value: rows.filter((row) => row.status === "completed").length },
  ];
  return { summary, rows };
}
