import type {
  DashboardData,
  QuestionList,
  QuestionOut,
  Workspace,
  ClaimEvidenceOut,
  EvaluationDataset,
  UnsupportedClaim,
} from "../types";

const BASE = ""; // Vite proxy routes /api and /switch to the backend.

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${body}`);
  }
  return (await r.json()) as T;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return (await r.json()) as T;
}

export const api = {
  // --- Health ---
  health: () => getJSON<{ status: string; switch_trust: Record<string, unknown>; mattermost: Record<string, unknown> }>("/api/health"),
  switchHealth: () => getJSON<Record<string, unknown>>("/switch/health"),

  // --- Dashboard ---
  dashboard: () => getJSON<DashboardData>("/api/dashboard"),
  evaluation: () => getJSON<EvaluationDataset>("/api/dashboard/evaluation"),

  // --- Questions ---
  listQuestions: () => getJSON<QuestionList[]>("/api/questions"),
  getQuestion: (id: string) => getJSON<QuestionOut>(`/api/questions/${id}`),
  createQuestion: (data: {
    question_text: string;
    language: "en" | "hi" | "pa";
    category: "scholarship" | "admission" | "scheme" | "general";
    platform?: string;
    external_user?: string;
  }) => postJSON<QuestionOut>("/api/questions", { platform: "web", ...data }),

  // --- Evidence inspector (per-claim source refs + freshness) ---
  getEvidence: (id: string) => getJSON<ClaimEvidenceOut[]>(`/api/questions/${id}/evidence`),

  // --- Unsupported claims (no source found — coordinator must check) ---
  getUnsupportedClaims: (id: string) => getJSON<UnsupportedClaim[]>(`/api/questions/${id}/unsupported-claims`),

  // --- Re-run research (coordinator requests another pass) ---
  rerunResearch: (id: string) => postJSON<{ accepted: boolean; status: string; message: string }>(`/api/questions/${id}/rerun-research`, {}),

  // --- Agent workspace ---
  workspace: (id: string) => getJSON<Workspace>(`/api/agents/question/${id}`),
  recentExecutions: () => getJSON<Workspace["executions"]>("/api/agents/executions"),

  // --- Human review ---
  review: (id: string, data: { action: "approved" | "rejected" | "corrections_requested"; reviewer_name: string; note?: string; secret?: string }) =>
    postJSON<{ id: string; action: string }>(`/api/review/${id}`, data),
  deliver: (id: string) => postJSON<{ delivered: boolean; final_text: string }>(`/api/review/${id}/deliver`, {}),
};
