/*
 * File: instructorMock.js
 * Owner: YUG
 * Purpose: Hold mock data for instructor and organiser page development.
 * What it is: Central demo data used by the dashboard, course form, reporting page, quiz builder, and content editor.
 */

export const instructorCourses = [
  {
    id: "odoo-ai",
    title: "Introduction to Odoo AI",
    tags: ["AI", "Automation", "Beginner"],
    views: 15,
    contents: 6,
    duration: "25:30",
    isPublished: true,
  },
  {
    id: "odoo-crm",
    title: "Basics of Odoo CRM",
    tags: ["CRM", "Sales", "Pipeline"],
    views: 20,
    contents: 8,
    duration: "20:35",
    isPublished: true,
  },
  {
    id: "odoo-courses",
    title: "About Odoo Courses",
    tags: ["Overview", "Admin", "Setup"],
    views: 10,
    contents: 5,
    duration: "10:20",
    isPublished: false,
  },
];

export const courseConfigMocks = {
  "new-course": {
    id: "new-course",
    title: "e.g: Basics of Odoo CRM",
    tags: [],
    isPublished: false,
    shareOnWeb: false,
    responsible: "Yug",
    courseAdmin: "Yug",
    visibility: "Everyone",
    accessRules: {
      open: true,
      invitation: false,
      payment: false,
    },
    price: "500",
    description: "Write the course-level description here.",
    imageLabel: "Course image",
    contentItems: [],
    quizzes: [],
  },
  "odoo-crm": {
    id: "odoo-crm",
    title: "Basics of Odoo CRM",
    tags: ["CRM", "Sales", "Pipeline"],
    isPublished: true,
    shareOnWeb: true,
    responsible: "Yug",
    courseAdmin: "Salman Khan",
    visibility: "Everyone",
    accessRules: {
      open: false,
      invitation: true,
      payment: true,
    },
    price: "500",
    description:
      "This course covers the functional configuration of Odoo CRM, including lead management, opportunity workflows, pipeline stages, and activity scheduling. It also explains CRM reporting, automation rules, and integration with Sales for end-to-end process handling.",
    imageLabel: "Course image",
    contentItems: [
      {
        id: "video-advanced-sales",
        title: "Advanced Sales & CRM Automation in Odoo",
        category: "Video",
      },
      {
        id: "doc-best-practices",
        title: "Odoo CRM: Advanced Features & Best Practices",
        category: "Document",
      },
      {
        id: "quiz-odoo-crm",
        title: "Quiz",
        category: "Quiz",
      },
    ],
    quizzes: [
      {
        id: "crm-quiz",
        title: "Quiz",
        category: "Quiz",
      },
    ],
  },
};

export const reportSummary = [
  { id: "participants", label: "Total Participants", value: 8 },
  { id: "yet-to-start", label: "Yet to Start", value: 5 },
  { id: "in-progress", label: "In Progress", value: 2 },
  { id: "completed", label: "Completed", value: 1 },
];

export const reportRows = [
  {
    id: 1,
    courseName: "Basics of Odoo CRM",
    participantName: "Salman Khan",
    enrolledDate: "Feb 14",
    startDate: "Feb 16",
    timeSpent: "2:20",
    completionPercentage: "30%",
    completedDate: "Feb 21",
    status: "In progress",
  },
];

export const quizBuilderMock = {
  id: "crm-quiz",
  title: "Pipeline Configuration Quiz",
  rewards: {
    first: 10,
    second: 7,
    third: 5,
    fourthPlus: 2,
  },
  questions: [
    {
      id: "question-1",
      prompt: "Write your question here",
      choices: [
        { id: "q1-a1", label: "Answer 1", isCorrect: true },
        { id: "q1-a2", label: "Answer 2", isCorrect: false },
        { id: "q1-a3", label: "Answer 3", isCorrect: false },
      ],
    },
    {
      id: "question-2",
      prompt: "Write your question here",
      choices: [
        { id: "q2-a1", label: "Answer 1", isCorrect: false },
        { id: "q2-a2", label: "Answer 2", isCorrect: true },
        { id: "q2-a3", label: "Answer 3", isCorrect: false },
      ],
    },
  ],
};

export const contentEditorMocks = {
  "video-advanced-sales": {
    id: "video-advanced-sales",
    title: "Advanced Sales & CRM Automation in Odoo",
    type: "Video",
    videoLink: "Google drive link or youtube video link is applicable",
    responsible: "Yug",
    duration: "00:00 hours",
    allowDownload: false,
    description: "Write your content description here...",
    attachmentFile: "",
    attachmentLink: "e.g : www.google.com",
  },
  "doc-best-practices": {
    id: "doc-best-practices",
    title: "Odoo CRM: Advanced Features & Best Practices",
    type: "Document",
    fileLabel: "Upload file",
    responsible: "Yug",
    allowDownload: true,
    description: "Write your content description here...",
    attachmentFile: "",
    attachmentLink: "e.g : www.google.com",
  },
  "image-advanced-sales": {
    id: "image-advanced-sales",
    title: "Advanced Sales & CRM Automation in Odoo",
    type: "Image",
    fileLabel: "Upload image",
    responsible: "Yug",
    allowDownload: true,
    description: "Write your content description here...",
    attachmentFile: "",
    attachmentLink: "e.g : www.google.com",
  },
};

export function getCourseConfigMock(courseId) {
  return courseConfigMocks[courseId] ?? courseConfigMocks["new-course"];
}

export function getContentEditorMock(contentId) {
  return contentEditorMocks[contentId] ?? contentEditorMocks["video-advanced-sales"];
}
