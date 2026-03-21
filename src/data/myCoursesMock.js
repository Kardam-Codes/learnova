/*
 * File: myCoursesMock.js
 * Owner: KARDAM
 * Purpose: Provide temporary My Courses page data until backend integration is ready.
 * What it is: Mock catalog and learner profile data that exercises start, continue, and buy states.
 */
import { PROFILE_BADGE_LEVEL } from "../../shared/types/common_types";

export const badgeTiers = [
  { name: PROFILE_BADGE_LEVEL.NEWBIE, minPoints: 0, maxPoints: 20 },
  { name: PROFILE_BADGE_LEVEL.EXPLORER, minPoints: 21, maxPoints: 40 },
  { name: PROFILE_BADGE_LEVEL.ACHIEVER, minPoints: 41, maxPoints: 60 },
  { name: PROFILE_BADGE_LEVEL.SPECIALIST, minPoints: 61, maxPoints: 80 },
  { name: PROFILE_BADGE_LEVEL.EXPERT, minPoints: 81, maxPoints: 100 },
  { name: PROFILE_BADGE_LEVEL.MASTER, minPoints: 101, maxPoints: 120 },
];

export const learnerProfileMock = {
  learnerName: "Kardam",
  totalPoints: 20,
  currentBadge: PROFILE_BADGE_LEVEL.NEWBIE,
  badgeTiers,
};

export const myCoursesMock = [
  {
    id: "odoo-crm",
    title: "Basics of Odoo CRM",
    shortDescription:
      "Build a clean sales pipeline, automate follow-ups, and close leads with confidence.",
    coverImage:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80",
    tags: ["CRM", "Automation", "Sales"],
    isPaid: false,
    price: null,
    isPurchased: true,
    isLoggedIn: true,
    hasStarted: true,
    isInProgress: true,
    detailPath: "/courses/odoo-crm",
    firstContentId: "advanced-sales-automation",
    lastContentId: "advanced-sales-automation",
  },
  {
    id: "lead-management",
    title: "Lead Management Essentials",
    shortDescription:
      "Create a repeatable inbound workflow and learn how to qualify leads faster.",
    coverImage:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80",
    tags: ["Leads", "Workflow", "CRM"],
    isPaid: false,
    price: null,
    isPurchased: true,
    isLoggedIn: true,
    hasStarted: false,
    isInProgress: false,
    detailPath: "/courses/lead-management",
    firstContentId: "lead-funnel-foundations",
    lastContentId: "lead-funnel-foundations",
  },
  {
    id: "crm-automation-pro",
    title: "CRM Automation Pro",
    shortDescription:
      "Design event-driven automations, smart triggers, and conversion-ready funnels.",
    coverImage:
      "https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80",
    tags: ["Automation", "Funnels", "Advanced"],
    isPaid: true,
    price: 500,
    isPurchased: false,
    isLoggedIn: true,
    hasStarted: false,
    isInProgress: false,
    detailPath: "/courses/crm-automation-pro",
    firstContentId: "automation-blueprints",
    lastContentId: "automation-blueprints",
  },
  {
    id: "crm-analytics",
    title: "CRM Analytics Playbook",
    shortDescription:
      "Use dashboards, reports, and weekly review rituals to improve team performance.",
    coverImage:
      "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80",
    tags: ["Analytics", "Reports", "Growth"],
    isPaid: true,
    price: 799,
    isPurchased: true,
    isLoggedIn: true,
    hasStarted: true,
    isInProgress: false,
    detailPath: "/courses/crm-analytics",
    firstContentId: "metrics-foundation",
    lastContentId: "retention-dashboard",
  },
];
