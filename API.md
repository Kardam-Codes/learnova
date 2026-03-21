# API.md

## Purpose
This document records:
- the **current frontend route contracts**
- the **planned backend API surface** for integration

The frontend is already built around these route/data expectations even where backend endpoints are still pending.

---

## Current Frontend Route Contracts

### Auth
- `GET /auth/login`
- `GET /auth/signup`
- `GET /auth/forgot-password`

### Learner Dashboard
- `GET /my-courses`

### Course Pages
- `GET /courses/:courseId`
- `GET /courses/:courseId/reviews`
- `GET /courses/:courseId/payment`

### Learning Routes
- `GET /courses/:courseId/learn/:contentId/document`
- `GET /courses/:courseId/learn/:contentId/video`
- `GET /courses/:courseId/learn/:contentId/quiz`
- `GET /courses/:courseId/learn/:contentId/quiz/question/:questionIndex`
- `GET /courses/:courseId/learn/:contentId/quiz/reward`

---

## Planned Backend API Contracts

## Auth

### `POST /auth/register`
Create a new user.

Request:
```json
{
  "name": "Kardam",
  "email": "kardam@example.com",
  "password": "StrongPass@123",
  "role": "learner"
}
```

Response:
```json
{
  "success": true,
  "message": "User created successfully"
}
```

### `POST /auth/login`
Authenticate a user.

Request:
```json
{
  "email": "kardam@example.com",
  "password": "StrongPass@123",
  "role": "learner"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "token": "jwt-or-session-token",
    "user": {
      "id": "user_1",
      "name": "Kardam",
      "email": "kardam@example.com",
      "role": "learner"
    }
  }
}
```

### `POST /auth/google`
Google auth handshake endpoint for backend verification when connected.

---

## Learner Course APIs

### `GET /courses`
Return visible/published courses based on role, visibility, and access rules.

### `GET /courses/:courseId`
Return learner-facing course detail page data:
- title
- short description
- thumbnail
- cover image
- progress summary
- ordered content list
- reviews summary

### `GET /courses/:courseId/reviews`
Return review summary and review list.

### `POST /courses/:courseId/reviews`
Create learner review.

Request:
```json
{
  "rating": 5,
  "comment": "Very helpful course"
}
```

### `GET /courses/:courseId/content`
Return ordered learning content for that course.

### `GET /courses/:courseId/content/:contentId`
Return one content item:
- mode: `document | video | quiz`
- description
- content URL
- attachments
- completion state

### `POST /courses/:courseId/content/:contentId/progress`
Update lesson completion / current position.

---

## Quiz APIs

### `GET /courses/:courseId/quizzes/:quizId`
Return quiz intro and question structure.

### `POST /courses/:courseId/quizzes/:quizId/attempt`
Submit one attempt.

Request:
```json
{
  "answers": [
    {
      "questionId": "q1",
      "selectedOptionIndex": 1
    }
  ]
}
```

Response:
```json
{
  "success": true,
  "data": {
    "attemptNumber": 1,
    "pointsEarned": 20,
    "nextTarget": 100,
    "message": "Reach the next rank to gain more points."
  }
}
```

---

## Instructor / Admin APIs

### Courses
- `GET /admin/courses`
- `POST /admin/courses`
- `GET /admin/courses/:courseId`
- `PUT /admin/courses/:courseId`
- `DELETE /admin/courses/:courseId`
- `POST /admin/courses/:courseId/publish`
- `POST /admin/courses/:courseId/unpublish`

### Lessons / Content
- `POST /admin/courses/:courseId/content`
- `PUT /admin/content/:contentId`
- `DELETE /admin/content/:contentId`

### Quizzes
- `GET /admin/courses/:courseId/quizzes`
- `POST /admin/courses/:courseId/quizzes`
- `PUT /admin/quizzes/:quizId`
- `DELETE /admin/quizzes/:quizId`

### Attendees
- `POST /admin/courses/:courseId/attendees`
- `POST /admin/courses/:courseId/contact-attendees`

### Reports
- `GET /admin/reports/courses`
- `GET /admin/reports/courses/:courseId`

---

## Shared Response Shape

Preferred API response envelope:

```json
{
  "success": true,
  "message": "Optional message",
  "data": {}
}
```

Error envelope:

```json
{
  "success": false,
  "message": "Human readable error",
  "errors": []
}
```
