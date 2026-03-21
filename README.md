# Learnova

Learnova is an eLearning platform with two major sides:
- Learner-facing website/app
- Instructor/Admin backoffice

The current repo status is strongest on the **learner-side frontend**, with route-driven pages for:
- authentication
- My Courses dashboard
- course detail overview
- ratings and reviews
- fullscreen lesson player
- quiz flow
- PDF.js document viewing

## Current Frontend Status

Implemented learner flows:
- Login / Signup
- Role selection in auth UI
- Google sign-in entry support
- My Courses dashboard
- Course Detail page
- Ratings and Reviews page
- Fullscreen lesson player
- Separate document / video / quiz route states
- Quiz intro, questions, reward flow
- Points / badge profile panel
- PDF.js document viewer with lazy loading, fullscreen, and keyboard shortcuts

## Current Frontend Architecture

The frontend currently follows a **page/component-based layered React structure**:

```plaintext
src/
├── components/
├── context/
├── data/
├── pages/
├── styles/
├── utils/
├── App.jsx
└── main.jsx
```

This is the current source of truth for frontend work.

## Current Stack

- Frontend: React + Vite
- Routing: React Router
- PDF Viewer: pdf.js (`pdfjs-dist`)
- Backend structure: Python-oriented placeholder/backend folders exist, but the main live product work in this repo is frontend-first at the moment
- Shared contracts: `shared/types/common_types.ts`

## Key Frontend Routes

- `/auth/login`
- `/auth/signup`
- `/auth/forgot-password`
- `/my-courses`
- `/courses/:courseId`
- `/courses/:courseId/reviews`
- `/courses/:courseId/payment`
- `/courses/:courseId/learn/:contentId/document`
- `/courses/:courseId/learn/:contentId/video`
- `/courses/:courseId/learn/:contentId/quiz`
- `/courses/:courseId/learn/:contentId/quiz/question/:questionIndex`
- `/courses/:courseId/learn/:contentId/quiz/reward`

## Local Setup

```bash
npm install
npm run dev
```

Build:

```bash
npm run build
```

## Environment

Use `.env.example` as the reference. Current frontend env usage:

```env
VITE_GOOGLE_CLIENT_ID=
```

## Important Project Conventions

- Use SVG icons only
- No emoji-based UI icons
- Add metadata headers in source files
- Keep ownership clear: `KARDAM`, `YUG`, or `BOTH CAN ADD`
- Keep new frontend pages inside the existing page/component structure

## Documentation Map

- [API.md](./API.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DB_SCHEMA.md](./DB_SCHEMA.md)
- [DESIGN.md](./DESIGN.md)
- [TASKS.md](./TASKS.md)
- [WORKFLOW.md](./WORKFLOW.md)
- [PAGE_CONSISTENCY.md](./PAGE_CONSISTENCY.md)
