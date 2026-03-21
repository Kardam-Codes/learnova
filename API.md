# 📡 API Documentation

## 🔐 Auth

POST /auth/register  
POST /auth/login  

---

## 📚 Courses

GET /courses  
POST /courses  
GET /courses/:id  
PUT /courses/:id  
DELETE /courses/:id  

---

## 📖 Lessons

POST /lessons  
GET /lessons/:courseId  
PUT /lessons/:id  
DELETE /lessons/:id  

---

## 📝 Quizzes

POST /quizzes  
GET /quizzes/:courseId  
POST /quizzes/attempt  

---

## ⭐ Reviews

POST /reviews  
GET /reviews/:courseId  

---

## 📊 Progress

GET /progress/:userId  
POST /progress/update  

---

## 📈 Reports

GET /reports/course/:id  

---

## 🧾 Example Response

```json
{
  "success": true,
  "data": {}
}