export interface Issue {
  id: string;
  tracking_id: string;
  category: string;
  locality: string;
  description: string;
  status: "submitted" | "progress" | "resolved";
  votes: number;
  attachment_url: string | null;
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface IssueStats {
  open: number;
  resolved: number;
  total: number;
}

import { getStoredAccessToken, getStoredRefreshToken, updateStoredAccessToken, clearStoredTokens } from "../auth/AuthContext";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const BASE_URL = "/api/v1";

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${BASE_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    clearStoredTokens();
    return null;
  }
  const body = await res.json();
  updateStoredAccessToken(body.access);
  return body.access as string;
}

async function request<T>(path: string, init?: RequestInit, _retried = false): Promise<T> {
  const access = getStoredAccessToken();

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
    ...init,
  });

  if (res.status === 401 && !_retried) {
    // Access token likely expired mid-session: try one silent refresh
    // before surfacing an error, so a 30-minute token lifetime doesn't
    // interrupt someone mid-report.
    const newAccess = await refreshAccessToken();
    if (newAccess) return request<T>(path, init, true);
  }

  if (!res.ok) {
    // The Django handler{400,403,404,500} views return this same JSON shape,
    // so a single ApiError type covers every failure mode from the API.
    const body = await res.json().catch(() => ({ message: res.statusText }));
    throw new ApiError(res.status, body.message ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export interface PresignResponse {
  upload_url: string;
  attachment_key: string;
  max_bytes: number;
}

export const api = {
  listIssues: () => request<{ results: Issue[] }>("/issues/"),
  createIssue: (payload: Pick<Issue, "category" | "locality" | "description"> & { attachment_key?: string }) =>
    request<Issue>("/issues/", { method: "POST", body: JSON.stringify(payload) }),
  upvote: (id: string) => request<Issue>(`/issues/${id}/upvote/`, { method: "PATCH" }),
  stats: () => request<IssueStats>("/issues/stats/"),
  updateStatus: (id: string, status: Issue["status"]) =>
    request<Issue>(`/issues/${id}/`, { method: "PATCH", body: JSON.stringify({ status }) }),
  presignUpload: (contentType: string) =>
    request<PresignResponse>("/issues/presign-upload/", {
      method: "POST",
      body: JSON.stringify({ content_type: contentType }),
    }),
  /** Uploads directly to S3 using the presigned URL — never touches Django. */
  uploadToS3: (uploadUrl: string, file: File) =>
    fetch(uploadUrl, { method: "PUT", headers: { "Content-Type": file.type }, body: file }).then((res) => {
      if (!res.ok) throw new ApiError(res.status, "Photo upload failed. Try a smaller image or a different format.");
    }),
  login: (username: string, password: string) =>
    fetch(`${BASE_URL}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then(async (res) => {
      if (!res.ok) throw new ApiError(res.status, "Invalid username or password");
      return res.json() as Promise<{ access: string; refresh: string }>;
    }),
};
