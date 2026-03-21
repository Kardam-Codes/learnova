## 📌 Architecture Style
Feature-Based Modular Architecture

Each feature (course, lesson, quiz) is self-contained with:
- model
- controller
- service
- routes

---

## 📦 Core Modules

### 1. Auth
- Login / Signup
- Role-based access (Admin, Learner)

### 2. Courses
- Create, edit, publish courses
- Manage course metadata

### 3. Lessons
- Types: Video, Document, Image
- Attachments support

### 4. Quizzes
- Question-based system
- Multiple attempts
- Reward logic

### 5. Progress
- Track lesson completion
- Course completion %

### 6. Reviews
- Ratings & feedback

### 7. Reports
- Course-wise analytics
- Learner progress tracking

---

## 🔄 Data Flow

Frontend → API → Service → DB → Response → UI

---

## 🎯 Design Principles

- Separation of concerns
- Feature isolation
- Scalable modules
- Clean API contracts