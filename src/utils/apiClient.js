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
