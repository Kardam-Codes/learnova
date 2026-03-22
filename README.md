# Learnova

Learnova is an eLearning platform with two product surfaces:

- learner-facing website
- instructor/admin backoffice

This repository contains the React frontend, the FastAPI backend, PostgreSQL schema and seed assets, and shared route/data contracts used across both sides.

## Stack

- Frontend: React 18 + Vite
- Routing: React Router
- PDF viewing: `pdfjs-dist`
- Backend: FastAPI + PostgreSQL
- Python DB drivers: `psycopg` or `psycopg2`
- Shared contracts: `shared/types/common_types.ts`

## Repo Structure

```plaintext
.
|- backend/
|  |- config/
|  |- db/
|  |- middleware/
|  |- modules/
|  `- main.py
|- shared/
|  |- constants/
|  `- types/
`- src/
   |- components/
   |- context/
   |- data/
   |- pages/
   |- styles/
   |- utils/
   |- App.jsx
   `- main.jsx
```

## Product Areas

### Learner Side

Implemented learner flows include:

- login and signup
- role-based auth entry
- Google sign-in entry support
- My Courses dashboard
- course detail page
- reviews page
- payment flow
- fullscreen lesson player
- document, video, and quiz route states
- quiz intro, question, and reward flow
- points and badge profile panel
- PDF.js viewer with lazy loading, fullscreen support, and keyboard shortcuts

### Instructor/Admin Side

The repo also includes instructor/admin routes and backend modules for:

- course creation and editing
- publishing and unpublishing
- attendee management
- content management
- quiz builder persistence
- reporting dashboard data
- uploads

## Frontend Architecture

The frontend uses a page/component-based layered structure.

```plaintext
src/
|- components/
|- context/
|- data/
|- pages/
|- styles/
|- utils/
|- App.jsx
`- main.jsx
```

Rules for frontend work:

- route-level screens belong in `src/pages`
- reusable UI belongs in `src/components`
- mock or generated demo data belongs in `src/data`
- helpers and route builders belong in `src/utils`
- shared styling belongs in `src/styles/app.css`
- do not introduce a second frontend architecture such as `src/modules/*` or `src/features/*`

## Backend Architecture

The backend is organized by capability inside `backend/modules`.

### Auth

- `backend/modules/auth/router.py`
- `backend/modules/auth/service.py`
- `backend/modules/auth/schemas.py`
- `backend/modules/auth/dependencies.py`

Responsibilities:

- register/login
- current user lookup
- token validation
- role guards

### Courses

- `backend/modules/courses/router.py`
- `backend/modules/courses/service.py`
- `backend/modules/courses/schemas.py`

Responsibilities:

- learner dashboard data
- course detail and reviews
- lesson/content loading
- progress updates
- quiz attempts and scoring
- enrollment and payment flow

### Admin

- `backend/modules/admin/router.py`
- `backend/modules/admin/service.py`
- `backend/modules/admin/schemas.py`

Responsibilities:

- admin/instructor course CRUD
- content CRUD
- quiz CRUD
- attendees
- uploads
- reporting

## Main Routes

### Frontend Routes

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

### Backend API Routes

#### Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/google`
- `GET /auth/me`

#### Learner Courses

- `GET /courses`
- `POST /courses/{course_slug}/enroll`
- `GET /courses/{course_slug}`
- `GET /courses/{course_slug}/reviews`
- `POST /courses/{course_slug}/reviews`
- `POST /courses/{course_slug}/payments/order`
- `POST /courses/{course_slug}/payments/verify`
- `GET /courses/{course_slug}/content/{content_slug}`
- `POST /courses/{course_slug}/content/{content_slug}/progress`
- `GET /courses/{course_slug}/quizzes/{content_slug}`
- `POST /courses/{course_slug}/quizzes/{content_slug}/attempts`

#### Admin

- `GET /admin/courses`
- `POST /admin/courses`
- `GET /admin/courses/{course_slug}`
- `PUT /admin/courses/{course_slug}`
- `DELETE /admin/courses/{course_slug}`
- `POST /admin/courses/{course_slug}/publish`
- `GET /admin/courses/{course_slug}/attendees`
- `POST /admin/courses/{course_slug}/attendees`
- `GET /admin/courses/{course_slug}/content`
- `POST /admin/courses/{course_slug}/content`
- `GET /admin/content/{content_slug}`
- `PUT /admin/content/{content_slug}`
- `DELETE /admin/content/{content_slug}`
- `GET /admin/courses/{course_slug}/quizzes`
- `POST /admin/courses/{course_slug}/quizzes`
- `GET /admin/quizzes/{quiz_id}`
- `PUT /admin/quizzes/{quiz_id}`
- `DELETE /admin/quizzes/{quiz_id}`
- `POST /admin/uploads`
- `GET /admin/reports/course-progress`

## Database

Learnova uses PostgreSQL.

Core database assets:

- `backend/db/schema.sql`
- `backend/db/seed.sql`
- `backend/db/migrations/001_extensions_and_enums.sql`
- `backend/db/migrations/002_core_entities.sql`
- `backend/db/migrations/003_learning_progress_and_reviews.sql`
- `backend/db/migrations/004_course_payment_orders.sql`
- `backend/db/migrations/005_quiz_attempt_answers_msq.sql`

### Main Tables

- `users`
- `courses`
- `course_tags`
- `course_tag_map`
- `course_attendees`
- `course_content`
- `content_attachments`
- `quizzes`
- `quiz_questions`
- `quiz_options`
- `quiz_reward_rules`
- `quiz_attempts`
- `quiz_attempt_answers`
- `course_progress`
- `content_progress`
- `learner_points`
- `point_events`
- `course_reviews`
- `course_payment_orders`

### Reporting

Reporting is driven by the `reporting_course_progress` view. It supports:

- course name
- participant name
- enrolled date
- start date
- time spent
- completion percentage
- completed date
- status

### Database Setup

Create the database:

```bash
psql -U postgres -c "CREATE DATABASE learnova;"
```

Run migrations:

```bash
psql -U postgres -d learnova -f backend/db/migrations/001_extensions_and_enums.sql
psql -U postgres -d learnova -f backend/db/migrations/002_core_entities.sql
psql -U postgres -d learnova -f backend/db/migrations/003_learning_progress_and_reviews.sql
psql -U postgres -d learnova -f backend/db/migrations/004_course_payment_orders.sql
psql -U postgres -d learnova -f backend/db/migrations/005_quiz_attempt_answers_msq.sql
```

Seed base demo data:

```bash
psql -U postgres -d learnova -f backend/db/seed.sql
```

Apply the full consolidated snapshot instead of migrations if needed:

```bash
psql -U postgres -d learnova -f backend/db/schema.sql
psql -U postgres -d learnova -f backend/db/seed.sql
```

## Bulk Data Generation

The repo includes a bulk SQL generator at `backend/db/load_bulk_schema_data.py`.

Available dataset modes:

- `generic`
- `reporting`
- `full`

### Generate 200 generic rows

```bash
python backend/db/load_bulk_schema_data.py --dataset generic --count 200
```

Output:

- `backend/db/bulk_seed_200.sql`

### Generate 40 reporting courses and 320 reporting rows

```bash
python backend/db/load_bulk_schema_data.py --dataset reporting --course-count 40 --reporting-rows 320
```

Output:

- `backend/db/reporting_seed_40_courses_320_rows.sql`

### Generate the combined full dataset

```bash
python backend/db/load_bulk_schema_data.py --dataset full --count 200 --course-count 40 --reporting-rows 320
```

Output:

- `backend/db/full_seed_200_courses_320_reporting_rows.sql`

Execute any generated SQL directly against PostgreSQL:

```bash
python backend/db/load_bulk_schema_data.py --dataset full --count 200 --course-count 40 --reporting-rows 320 --execute
```

## Local Development

### Frontend

```bash
npm install
npm run dev
```

Build:

```bash
npm run build
```

### Backend

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Run the API:

```bash
uvicorn backend.main:app --reload
```

## Environment

Frontend:

```env
VITE_GOOGLE_CLIENT_ID=
VITE_API_BASE_URL=
```

Backend database settings are read from `DATABASE_URL` or from:

```env
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

Payment and auth integrations may also require additional environment values depending on the local setup.

## Current Demo Fallbacks

The repo contains generated demo-data helpers in `src/data/generatedDemoData.js` so the UI can still render large catalog and reporting scenarios during local development when the live backend is unavailable or undersized.

## Working Rules

### File Metadata

Source files should include a short metadata header such as:

```js
/*
 * File: ExamplePage.jsx
 * Owner: KARDAM | YUG | BOTH CAN ADD
 * Purpose: One-line reason this file exists.
 * What it is: Short description of what this file renders or controls.
 */
```

### Ownership

Ownership markers used in the repo:

- `KARDAM`
- `YUG`
- `BOTH CAN ADD`

### UI Conventions

- use SVG icons only
- do not use emojis as UI icons
- preserve the existing navbar, card, border, and spacing language
- keep light/dark theme support aligned with current CSS variables
- reuse the current page/component structure instead of introducing a second UI system

### Workflow

Recommended flow:

1. pull latest changes
2. work in the appropriate branch
3. keep commits focused
4. build and test locally
5. push the branch
6. merge into `main`

Suggested commit prefixes:

- `feat:`
- `fix:`
- `docs:`
- `chore:`
- `refactor:`

### Current Responsibility Split

Kardam:

- learner-side frontend
- auth frontend
- learner navigation and UX
- shared frontend visual system

Yug:

- backend logic
- instructor/admin implementation
- API wiring
- domain and data flow

Shared:

- integration
- shared contracts and constants
- QA
- bug fixes

## Priority Order

1. keep learner flow stable
2. keep instructor/admin flow aligned with the same frontend system
3. connect live backend APIs across the learner pages
4. replace small mock-only flows with integrated data
5. finish reporting, persistence, and QA
