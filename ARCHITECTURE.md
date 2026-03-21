# ARCHITECTURE.md

## Current Reality
This repo currently has:
- a **live learner-side React frontend**
- a **planned / partial backend structure**
- shared constants and types

So the architecture should be understood in two layers:
- current frontend architecture
- planned backend/domain architecture

---

## 1. Current Frontend Architecture

The frontend currently uses a:

**Page/Component-Based Layered React Architecture**

Structure:

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

### Meaning
- `pages/`: route-level screens
- `components/`: reusable UI units
- `context/`: app-wide state such as auth
- `data/`: mock/demo data until backend APIs are connected
- `utils/`: route builders and frontend helpers
- `styles/`: shared visual system

### Why this matters
This is the actual current source of truth for frontend implementation.

Do not treat the frontend as feature-module based unless the whole frontend is intentionally refactored later.

---

## 2. Current Frontend Flow

### Auth Flow
- Login page
- Signup page
- Forgot-password modal flow
- Role selection in auth UI
- Google sign-in entry support

### Learner Flow
- My Courses dashboard
- Course Detail page
- Ratings and Reviews page
- Fullscreen lesson player
- Separate document/video/quiz route states
- Quiz intro -> question pages -> reward route
- PDF.js document viewing

---

## 3. Planned Backend / Domain Architecture

The backend/domain direction is still modular by capability:

```plaintext
backend/
├── config/
├── middleware/
└── modules/
```

Logical modules:
- auth
- users
- courses
- lessons/content
- quizzes
- progress
- reviews
- reports

This is the **domain/backend architecture direction**, even though the frontend does not mirror it folder-for-folder.

---

## 4. Shared Layer

Shared files live under:

```plaintext
shared/
├── constants/
└── types/
```

Use this layer for:
- shared enums
- shared app constants
- lightweight contracts reused across frontend/backend planning

Current important file:
- `shared/types/common_types.ts`

---

## 5. Data Flow

### Current Frontend Flow
```plaintext
Page -> Mock Data / Context -> Components -> UI
```

### Target Integrated Flow
```plaintext
UI -> Route/Page -> API call -> Backend service/domain -> DB -> Response -> UI
```

---

## 6. Routing Model

The frontend already uses route-driven state for learning content.

Examples:
- `/my-courses`
- `/courses/:courseId`
- `/courses/:courseId/reviews`
- `/courses/:courseId/learn/:contentId/document`
- `/courses/:courseId/learn/:contentId/video`
- `/courses/:courseId/learn/:contentId/quiz`

This route-driven structure is intentional and should be preserved.

---

## 7. State Management

Current state approach:
- local component state for UI interactions
- `AuthContext` for auth/session-like frontend state
- mock data for learner content and progress rendering

This is enough for the current stage.

No global state library is required right now.

---

## 8. Design Principles

- Keep frontend architecture simple and explicit
- Reuse shared UI components before adding new page-specific one-offs
- Keep mock data out of page JSX when possible
- Preserve route clarity
- Do not create empty scaffolding
- Prefer readable ownership and metadata headers

---

## 9. Important Constraint

For new instructor/admin frontend work:
- follow the current frontend page/component structure
- do not create a second frontend architecture inside `src`

See:
- [PAGE_CONSISTENCY.md](./PAGE_CONSISTENCY.md)
