/*
 * File: courseDetailMock.js
 * Owner: KARDAM
 * Purpose: Provide detail-page mock data for multiple learner courses.
 * What it is: Temporary lookup-based course detail data used by overview, reviews, and player routes.
 */
import {
  COURSE_CONTENT_STATUS,
  COURSE_CONTENT_TYPE,
} from "../../shared/types/common_types";

const sharedProvider = {
  providerName: "KaiCrypt",
  learnerName: "Kardam",
};

export const courseDetailMockById = {
  "odoo-crm": {
    id: "odoo-crm",
    title: "Basics of Odoo CRM",
    shortDescription:
      "Learn how to structure pipelines, automate sales stages, and manage leads inside Odoo CRM.",
    thumbnail:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1600&q=80",
    ...sharedProvider,
    progress: {
      completionPercentage: 30,
      totalCount: 4,
      completedCount: 1,
      incompleteCount: 3,
    },
    contentItems: [
      {
        id: "advanced-sales-automation",
        title: "Advanced Sales & CRM Automation in Odoo",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.IN_PROGRESS,
        order: 1,
        duration: "14 min",
        description: "Set up smart activities, deal stages, and team workflows.",
      },
      {
        id: "odoo-best-practices",
        title: "Odoo CRM: Advanced Features & Best Practices",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 2,
        duration: "11 min",
        description: "Use tags, filters, and reporting to build a disciplined funnel.",
      },
      {
        id: "pipeline-quiz",
        title: "Pipeline Configuration Quiz",
        type: COURSE_CONTENT_TYPE.QUIZ,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 3,
        duration: "6 questions",
        description: "Quick assessment on lead stages, activities, and automation.",
      },
      {
        id: "lead-management-templates",
        title: "Lead Management Templates",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 4,
        duration: "9 min",
        description: "Apply reusable templates to improve follow-up consistency.",
      },
    ],
  },
  "lead-management": {
    id: "lead-management",
    title: "Lead Management Essentials",
    shortDescription:
      "Create a repeatable inbound workflow and learn how to qualify leads faster.",
    thumbnail:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1600&q=80",
    ...sharedProvider,
    progress: {
      completionPercentage: 0,
      totalCount: 4,
      completedCount: 0,
      incompleteCount: 4,
    },
    contentItems: [
      {
        id: "lead-funnel-foundations",
        title: "Lead Funnel Foundations",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 1,
        duration: "12 min",
        description: "Understand qualification stages and healthy lead movement.",
      },
      {
        id: "lead-scoring-framework",
        title: "Lead Scoring Framework",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 2,
        duration: "10 min",
        description: "Create a simple scoring system for inbound opportunities.",
      },
      {
        id: "lead-response-quiz",
        title: "Lead Response Time Quiz",
        type: COURSE_CONTENT_TYPE.QUIZ,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 3,
        duration: "5 questions",
        description: "Check how quickly your playbook should react to new leads.",
      },
      {
        id: "handoff-checklist",
        title: "Sales Handoff Checklist",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 4,
        duration: "8 min",
        description: "Finalize a clean transition from marketing to sales.",
      },
    ],
  },
  "crm-automation-pro": {
    id: "crm-automation-pro",
    title: "CRM Automation Pro",
    shortDescription:
      "Design event-driven automations, smart triggers, and conversion-ready funnels.",
    thumbnail:
      "https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1600&q=80",
    ...sharedProvider,
    progress: {
      completionPercentage: 0,
      totalCount: 4,
      completedCount: 0,
      incompleteCount: 4,
    },
    contentItems: [
      {
        id: "automation-blueprints",
        title: "Automation Blueprints",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 1,
        duration: "16 min",
        description: "Map trigger-based automations for lead movement and nurturing.",
      },
      {
        id: "trigger-design",
        title: "Trigger Design Patterns",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 2,
        duration: "13 min",
        description: "Choose the right event model for workflows that scale.",
      },
      {
        id: "automation-quiz",
        title: "Automation Logic Quiz",
        type: COURSE_CONTENT_TYPE.QUIZ,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 3,
        duration: "7 questions",
        description: "Validate your understanding of trigger conditions and actions.",
      },
      {
        id: "handover-automation",
        title: "Sales Handover Automation",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.NOT_STARTED,
        order: 4,
        duration: "9 min",
        description: "Automate the transition from qualified lead to deal owner.",
      },
    ],
  },
  "crm-analytics": {
    id: "crm-analytics",
    title: "CRM Analytics Playbook",
    shortDescription:
      "Use dashboards, reports, and weekly review rituals to improve team performance.",
    thumbnail:
      "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80",
    coverImage:
      "https://images.unsplash.com/photo-1518186233392-c232efbf2373?auto=format&fit=crop&w=1600&q=80",
    ...sharedProvider,
    progress: {
      completionPercentage: 75,
      totalCount: 4,
      completedCount: 3,
      incompleteCount: 1,
    },
    contentItems: [
      {
        id: "metrics-foundation",
        title: "Metrics Foundation",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 1,
        duration: "15 min",
        description: "Identify the metrics that actually change revenue performance.",
      },
      {
        id: "pipeline-reporting",
        title: "Pipeline Reporting",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 2,
        duration: "12 min",
        description: "Build a weekly reporting rhythm around lead and deal health.",
      },
      {
        id: "analytics-quiz",
        title: "Analytics Interpretation Quiz",
        type: COURSE_CONTENT_TYPE.QUIZ,
        status: COURSE_CONTENT_STATUS.COMPLETED,
        order: 3,
        duration: "6 questions",
        description: "Test how well you can read dashboards and spot warning signs.",
      },
      {
        id: "retention-dashboard",
        title: "Retention Dashboard",
        type: COURSE_CONTENT_TYPE.LESSON,
        status: COURSE_CONTENT_STATUS.IN_PROGRESS,
        order: 4,
        duration: "10 min",
        description: "Build a retention view that keeps churn risk visible.",
      },
    ],
  },
};

export const courseDetailMock = courseDetailMockById["odoo-crm"];

export function getCourseDetailMock(courseId) {
  return courseDetailMockById[courseId] ?? courseDetailMock;
}
