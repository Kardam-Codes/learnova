# 🗂️ 4. `DB_SCHEMA.md`

```md id="db-schema-md"
# 🗂️ Database Schema

## 👤 Users
- id
- name
- email
- password
- role (admin / learner/ instructor)

---

## 📚 Courses
- id
- title
- description
- tags
- isPublished
- createdBy

---

## 📖 Lessons
- id
- courseId
- title
- type (video/document/image)
- contentUrl
- description

---

## 📝 Quizzes
- id
- courseId

### Questions
- id
- quizId
- question
- options[]
- correctAnswer

---

## 🎯 Attempts
- id
- userId
- quizId
- attemptNumber
- score

---

## 📊 Progress
- id
- userId
- courseId
- completionPercentage

---

## ⭐ Reviews
- id
- userId
- courseId
- rating
- comment