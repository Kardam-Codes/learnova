/*
 * File: apiClient.js
 * Owner: KARDAM
 * Purpose: Centralize frontend HTTP calls to the Learnova backend.
 * What it is: Small fetch helpers for auth and learner course endpoints.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseJsonResponse(response) {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      "The request could not be completed.";
    throw new Error(message);
  }

  return data;
}

function buildHeaders(token) {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function buildAuthHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginRequest(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function registerRequest(payload) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function meRequest(token) {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchCoursesRequest(token) {
  const response = await fetch(`${API_BASE_URL}/courses`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchCourseDetailRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchCourseReviewsRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/reviews`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function enrollCourseRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/enroll`, {
    method: "POST",
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function submitCourseReviewRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/reviews`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function fetchCourseContentRequest(courseId, contentId, token) {
  const response = await fetch(
    `${API_BASE_URL}/courses/${courseId}/content/${contentId}`,
    {
      headers: buildHeaders(token),
    },
  );

  return parseJsonResponse(response);
}

export async function createCoursePaymentOrderRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/payments/order`, {
    method: "POST",
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function verifyCoursePaymentRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/courses/${courseId}/payments/verify`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function updateCourseContentProgressRequest(courseId, contentId, token, payload) {
  const response = await fetch(
    `${API_BASE_URL}/courses/${courseId}/content/${contentId}/progress`,
    {
      method: "POST",
      headers: buildHeaders(token),
      body: JSON.stringify(payload),
    },
  );

  return parseJsonResponse(response);
}

export async function fetchQuizRequest(courseId, contentId, token) {
  const response = await fetch(
    `${API_BASE_URL}/courses/${courseId}/quizzes/${contentId}`,
    {
      headers: buildHeaders(token),
    },
  );

  return parseJsonResponse(response);
}

export async function submitQuizAttemptRequest(courseId, contentId, token, payload) {
  const response = await fetch(
    `${API_BASE_URL}/courses/${courseId}/quizzes/${contentId}/attempts`,
    {
      method: "POST",
      headers: buildHeaders(token),
      body: JSON.stringify(payload),
    },
  );

  return parseJsonResponse(response);
}

export async function fetchAdminCoursesRequest(token) {
  const response = await fetch(`${API_BASE_URL}/admin/courses`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminUsersRequest(token, roles) {
  const query = roles?.length ? `?roles=${encodeURIComponent(roles.join(","))}` : "";
  const response = await fetch(`${API_BASE_URL}/admin/users${query}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminCourseRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function createAdminCourseRequest(token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/courses`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function updateAdminCourseRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function publishAdminCourseRequest(courseId, token, isPublished) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/publish`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ isPublished }),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminCourseAttendeesRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/attendees`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function addAdminCourseAttendeesRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/attendees`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminCourseContentRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/content`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function createAdminCourseContentRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/content`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminContentRequest(contentId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/content/${contentId}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function updateAdminContentRequest(contentId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/content/${contentId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function deleteAdminContentRequest(contentId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/content/${contentId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminCourseQuizzesRequest(courseId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/quizzes`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function createAdminQuizRequest(courseId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/courses/${courseId}/quizzes`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminQuizRequest(quizId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/quizzes/${quizId}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function updateAdminQuizRequest(quizId, token, payload) {
  const response = await fetch(`${API_BASE_URL}/admin/quizzes/${quizId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function deleteAdminQuizRequest(quizId, token) {
  const response = await fetch(`${API_BASE_URL}/admin/quizzes/${quizId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function fetchAdminCourseProgressReportRequest(token, status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await fetch(`${API_BASE_URL}/admin/reports/course-progress${query}`, {
    headers: buildHeaders(token),
  });

  return parseJsonResponse(response);
}

export async function uploadAdminFileRequest(token, file, category = "attachments") {
  const formData = new FormData();
  formData.append("category", category);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/admin/uploads`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });

  return parseJsonResponse(response);
}
