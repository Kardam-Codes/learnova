/*
 * File: courseDetailMock.js
 * Owner: KARDAM
 * Purpose: Provide detail-page mock data for multiple learner courses.
 * What it is: Temporary lookup-based course detail, review, and learning-route data used by overview, reviews, and player routes.
 */
import {
  COURSE_CONTENT_STATUS,
  COURSE_CONTENT_TYPE,
  LEARNING_CONTENT_MODE,
} from "../../shared/types/common_types";

const sharedProvider = {
  providerName: "KaiCrypt",
  learnerName: "Kardam",
};

function createReviewSummary(averageRating, items, learnerDraft) {
  return {
    averageRating,
    totalReviews: items.length,
    items,
    learnerDraft,
  };
}

function createAttachment(id, label, url) {
  return { id, label, url };
}

function createLesson({
  id,
  title,
  mode,
  status,
  order,
  duration,
  description,
  contentUrl,
  attachments,
  nextContentId,
}) {
  return {
    id,
    title,
    type: COURSE_CONTENT_TYPE.LESSON,
    mode,
    status,
    order,
    duration,
    description,
    contentUrl,
    attachments,
    nextContentId,
  };
}

function createQuiz({
  id,
  title,
  status,
  order,
  duration,
  description,
  nextContentId,
  reward,
  quizQuestions,
}) {
  return {
    id,
    title,
    type: COURSE_CONTENT_TYPE.QUIZ,
    mode: LEARNING_CONTENT_MODE.QUIZ,
    status,
    order,
    duration,
    description,
    nextContentId,
    quizRules: {
      totalQuestions: quizQuestions.length,
      maxAttempts: 3,
    },
    quizQuestions,
    reward,
  };
}

const odooContentItems = [
  createVideoContent(),
  createDocumentContent(),
  createQuizContent(),
  createWrapUpContent(),
];

function createVideoContent() {
  return createLesson({
    id: "advanced-sales-automation",
    title: "Advanced Sales & CRM Automation in Odoo",
    mode: LEARNING_CONTENT_MODE.VIDEO,
    status: COURSE_CONTENT_STATUS.IN_PROGRESS,
    order: 1,
    duration: "14 min",
    description:
      "Watch how pipeline automation, activity suggestions, and sales team stages fit together inside Odoo CRM.",
    contentUrl: "https://www.youtube.com/embed/dQw4w9WgXcQ",
    attachments: [
      createAttachment(
        "sales-blueprint",
        "Sales blueprint PDF",
        "https://example.com/sales-blueprint.pdf",
      ),
    ],
    nextContentId: "odoo-best-practices",
  });
}

function createDocumentContent() {
  return createLesson({
    id: "odoo-best-practices",
    title: "Odoo CRM: Advanced Features & Best Practices",
    mode: LEARNING_CONTENT_MODE.DOCUMENT,
    status: COURSE_CONTENT_STATUS.COMPLETED,
    order: 2,
    duration: "11 min",
    description:
      "Read the best-practice checklist covering segmentation, tags, saved filters, and weekly pipeline hygiene.",
    contentUrl:
      "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    attachments: [
      createAttachment(
        "best-practice-sheet",
        "Best practice checklist",
        "https://example.com/best-practice-checklist.pdf",
      ),
    ],
    nextContentId: "pipeline-quiz",
  });
}

function createQuizContent() {
  return createQuiz({
    id: "pipeline-quiz",
    title: "Pipeline Configuration Quiz",
    status: COURSE_CONTENT_STATUS.NOT_STARTED,
    order: 3,
    duration: "3 questions",
    description:
      "Answer a quick quiz on stage automation, lead scoring, and follow-up discipline before unlocking the final content.",
    nextContentId: "lead-management-templates",
    reward: {
      pointsEarned: 20,
      nextTarget: 100,
      message: "Reach the next rank to gain more points.",
    },
    quizQuestions: [
      {
        id: "pipeline-q1",
        prompt: "Which automation best reduces follow-up delay for new qualified leads?",
        options: [
          "Manual daily tracking only",
          "Automatic activity assignment after qualification",
          "Removing lead stages completely",
        ],
        correctOptionIndex: 1,
      },
      {
        id: "pipeline-q2",
        prompt: "Why should a team use lead stages consistently in Odoo CRM?",
        options: [
          "To reduce reporting clarity",
          "To make dashboards and ownership less reliable",
          "To keep pipeline reporting and handoff behavior structured",
        ],
        correctOptionIndex: 2,
      },
      {
        id: "pipeline-q3",
        prompt: "Which practice usually improves lead prioritization?",
        options: [
          "Lead scoring rules tied to intent signals",
          "Random assignment with no conditions",
          "Ignoring contact source data",
        ],
        correctOptionIndex: 0,
      },
    ],
  });
}

function createWrapUpContent() {
  return createLesson({
    id: "lead-management-templates",
    title: "Lead Management Templates",
    mode: LEARNING_CONTENT_MODE.DOCUMENT,
    status: COURSE_CONTENT_STATUS.NOT_STARTED,
    order: 4,
    duration: "9 min",
    description:
      "Use repeatable lead templates and handoff notes to make the final stretch of your CRM workflow easier to execute.",
    contentUrl:
      "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    attachments: [
      createAttachment(
        "lead-template-pack",
        "Lead template pack",
        "https://example.com/lead-templates.pdf",
      ),
    ],
    nextContentId: null,
  });
}

function buildCourse({
  id,
  title,
  shortDescription,
  thumbnail,
  coverImage,
  progress,
  contentItems,
  reviews,
}) {
  return {
    id,
    title,
    shortDescription,
    thumbnail,
    coverImage,
    ...sharedProvider,
    progress,
    contentItems,
    reviews,
  };
}

export const courseDetailMockById = {
  "odoo-crm": buildCourse({
    id: "odoo-crm",
    title: "Basics of Odoo CRM",
    shortDescription:
      "Learn how to structure pipelines, automate sales stages, and manage leads inside Odoo CRM.",
    thumbnail:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1600&q=80",
    progress: {
      completionPercentage: 30,
      totalCount: 4,
      completedCount: 1,
      incompleteCount: 3,
    },
    contentItems: odooContentItems,
    reviews: createReviewSummary(
      4.5,
      [
        {
          id: "review-1",
          authorName: "Kardam",
          rating: 5,
          comment: "Clear explanations and a very practical walkthrough of stage automation.",
        },
        {
          id: "review-2",
          authorName: "Aman Gupta",
          rating: 4,
          comment: "The examples were useful and the documents helped reinforce the video.",
        },
        {
          id: "review-3",
          authorName: "Rhea Singh",
          rating: 4,
          comment: "A strong beginner CRM module with enough depth to feel actionable.",
        },
      ],
      "This course made pipeline setup much easier to understand.",
    ),
  }),
  "lead-management": buildCourse({
    id: "lead-management",
    title: "Lead Management Essentials",
    shortDescription:
      "Create a repeatable inbound workflow and learn how to qualify leads faster.",
    thumbnail:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1600&q=80",
    progress: {
      completionPercentage: 0,
      totalCount: 4,
      completedCount: 0,
      incompleteCount: 4,
    },
    contentItems: [
      createLesson({
        id: "lead-funnel-foundations",
        title: "Lead Funnel Foundations",
        mode: LEARNING_CONTENT_MODE.VIDEO,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 1,
        duration: "12 min",
        description: "A practical overview of qualification stages and healthy lead movement.",
        contentUrl: "https://www.youtube.com/embed/ysz5S6PUM-U",
        attachments: [
          createAttachment("lead-map", "Lead funnel map", "https://example.com/funnel-map.pdf"),
        ],
        nextContentId: "lead-scoring-framework",
      }),
      createLesson({
        id: "lead-scoring-framework",
        title: "Lead Scoring Framework",
        mode: LEARNING_CONTENT_MODE.DOCUMENT,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 2,
        duration: "10 min",
        description: "Set up a lightweight lead scoring model for better handoff decisions.",
        contentUrl:
          "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        attachments: [
          createAttachment("lead-score-sheet", "Lead scoring sheet", "https://example.com/scoring.pdf"),
        ],
        nextContentId: "lead-response-quiz",
      }),
      createQuiz({
        id: "lead-response-quiz",
        title: "Lead Response Time Quiz",
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 3,
        duration: "3 questions",
        description: "Check how quickly your playbook should respond to high-intent leads.",
        nextContentId: "handoff-checklist",
        reward: {
          pointsEarned: 15,
          nextTarget: 100,
          message: "Stay consistent and you will unlock the next badge sooner.",
        },
        quizQuestions: [
          {
            id: "lead-q1",
            prompt: "What usually improves conversion on inbound leads?",
            options: ["Faster response time", "More silence", "No qualification notes"],
            correctOptionIndex: 0,
          },
          {
            id: "lead-q2",
            prompt: "What should handoff notes include?",
            options: ["Intent signal and next step", "Nothing but email", "Only random tags"],
            correctOptionIndex: 0,
          },
          {
            id: "lead-q3",
            prompt: "Which rule helps prioritize a lead?",
            options: ["Source and activity score", "Random queue order", "Ignoring replies"],
            correctOptionIndex: 0,
          },
        ],
      }),
      createLesson({
        id: "handoff-checklist",
        title: "Sales Handoff Checklist",
        mode: LEARNING_CONTENT_MODE.DOCUMENT,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 4,
        duration: "8 min",
        description: "Finalize a clean transition from marketing to sales.",
        contentUrl:
          "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        attachments: [],
        nextContentId: null,
      }),
    ],
    reviews: createReviewSummary(
      4.2,
      [
        {
          id: "lead-review-1",
          authorName: "Nitika",
          rating: 4,
          comment: "Useful if you are building your first real lead management workflow.",
        },
      ],
      "Helpful structure and clean examples.",
    ),
  }),
  "crm-automation-pro": buildCourse({
    id: "crm-automation-pro",
    title: "CRM Automation Pro",
    shortDescription:
      "Design event-driven automations, smart triggers, and conversion-ready funnels.",
    thumbnail:
      "https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1600&q=80",
    progress: {
      completionPercentage: 0,
      totalCount: 4,
      completedCount: 0,
      incompleteCount: 4,
    },
    contentItems: [
      createLesson({
        id: "automation-blueprints",
        title: "Automation Blueprints",
        mode: LEARNING_CONTENT_MODE.VIDEO,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 1,
        duration: "16 min",
        description: "Map trigger-based automations for lead movement and nurturing.",
        contentUrl: "https://www.youtube.com/embed/aqz-KE-bpKQ",
        attachments: [],
        nextContentId: "trigger-design",
      }),
      createLesson({
        id: "trigger-design",
        title: "Trigger Design Patterns",
        mode: LEARNING_CONTENT_MODE.DOCUMENT,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 2,
        duration: "13 min",
        description: "Choose the right event model for workflows that scale.",
        contentUrl:
          "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        attachments: [],
        nextContentId: "automation-quiz",
      }),
      createQuiz({
        id: "automation-quiz",
        title: "Automation Logic Quiz",
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 3,
        duration: "3 questions",
        description: "Validate your understanding of trigger conditions and actions.",
        nextContentId: "handover-automation",
        reward: {
          pointsEarned: 25,
          nextTarget: 120,
          message: "Strong automation habits help you move toward the next rank.",
        },
        quizQuestions: [
          {
            id: "automation-q1",
            prompt: "What should trigger a lead nurture sequence?",
            options: ["A meaningful qualification event", "Random clock changes", "No user action at all"],
            correctOptionIndex: 0,
          },
          {
            id: "automation-q2",
            prompt: "Why are reusable patterns helpful?",
            options: ["They reduce consistency", "They speed up safe implementation", "They remove testing"],
            correctOptionIndex: 1,
          },
          {
            id: "automation-q3",
            prompt: "What is a good handover automation outcome?",
            options: ["No owner assigned", "Clear next step and ownership", "Deleted activity history"],
            correctOptionIndex: 1,
          },
        ],
      }),
      createLesson({
        id: "handover-automation",
        title: "Sales Handover Automation",
        mode: LEARNING_CONTENT_MODE.VIDEO,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 4,
        duration: "9 min",
        description: "Automate the transition from qualified lead to deal owner.",
        contentUrl: "https://www.youtube.com/embed/ScMzIvxBSi4",
        attachments: [],
        nextContentId: null,
      }),
    ],
    reviews: createReviewSummary(
      4.7,
      [
        {
          id: "automation-review-1",
          authorName: "Yug",
          rating: 5,
          comment: "Very sharp explanations for trigger-based CRM automation.",
        },
      ],
      "Looks advanced but still feels teachable.",
    ),
  }),
  "crm-analytics": buildCourse({
    id: "crm-analytics",
    title: "CRM Analytics Playbook",
    shortDescription:
      "Use dashboards, reports, and weekly review rituals to improve team performance.",
    thumbnail:
      "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1518186233392-c232efbf2373?auto=format&fit=crop&w=1600&q=80",
    progress: {
      completionPercentage: 75,
      totalCount: 4,
      completedCount: 3,
      incompleteCount: 1,
    },
    contentItems: [
      createLesson({
        id: "metrics-foundation",
        title: "Metrics Foundation",
        mode: LEARNING_CONTENT_MODE.VIDEO,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 1,
        duration: "15 min",
        description: "Identify the metrics that actually change revenue performance.",
        contentUrl: "https://www.youtube.com/embed/M7lc1UVf-VE",
        attachments: [],
        nextContentId: "pipeline-reporting",
      }),
      createLesson({
        id: "pipeline-reporting",
        title: "Pipeline Reporting",
        mode: LEARNING_CONTENT_MODE.DOCUMENT,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 2,
        duration: "12 min",
        description: "Build a weekly reporting rhythm around lead and deal health.",
        contentUrl:
          "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        attachments: [],
        nextContentId: "analytics-quiz",
      }),
      createQuiz({
        id: "analytics-quiz",
        title: "Analytics Interpretation Quiz",
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 3,
        duration: "3 questions",
        description: "Test how well you can read dashboards and spot warning signs.",
        nextContentId: "retention-dashboard",
        reward: {
          pointsEarned: 20,
          nextTarget: 120,
          message: "One more strong module and you move closer to Expert.",
        },
        quizQuestions: [
          {
            id: "analytics-q1",
            prompt: "What makes a pipeline dashboard useful?",
            options: ["Clear stage metrics", "No context", "Only vanity counts"],
            correctOptionIndex: 0,
          },
          {
            id: "analytics-q2",
            prompt: "Which signal often points to risk?",
            options: ["Shrinking response speed", "Consistent follow-up", "Healthy conversion"],
            correctOptionIndex: 0,
          },
          {
            id: "analytics-q3",
            prompt: "What should a weekly review do?",
            options: ["Ignore trend changes", "Drive corrective decisions", "Remove accountability"],
            correctOptionIndex: 1,
          },
        ],
      }),
      createLesson({
        id: "retention-dashboard",
        title: "Retention Dashboard",
        mode: LEARNING_CONTENT_MODE.DOCUMENT,
        status: COURSE_CONTENT_STATUS.IN_PROGRESS,
        order: 4,
        duration: "10 min",
        description: "Build a retention view that keeps churn risk visible.",
        contentUrl:
          "https://docs.google.com/gview?embedded=1&url=https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        attachments: [
          createAttachment(
            "retention-template",
            "Retention dashboard template",
            "https://example.com/retention.pdf",
          ),
        ],
        nextContentId: null,
      }),
    ],
    reviews: createReviewSummary(
      4.8,
      [
        {
          id: "analytics-review-1",
          authorName: "Parth",
          rating: 5,
          comment: "Great structure for learning how to read and act on CRM dashboards.",
        },
      ],
      "This analytics flow felt practical and easy to apply.",
    ),
  }),
};

export const courseDetailMock = courseDetailMockById["odoo-crm"];

export function getCourseDetailMock(courseId) {
  return courseDetailMockById[courseId] ?? courseDetailMock;
}
