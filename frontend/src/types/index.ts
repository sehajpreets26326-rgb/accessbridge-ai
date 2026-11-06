// Shared types matching the backend Pydantic schemas.

export type Language = "en" | "hi" | "pa";
export type Category = "scholarship" | "admission" | "scheme" | "general";

export interface QuestionList {
  id: string;
  question_text: string;
  language: Language;
  category: Category;
  status: string;
  created_at: string;
  external_user: string | null;
}

export interface QuestionOut extends QuestionList {
  platform: string;
  channel: string;
  updated_at: string;
  error_message: string | null;
}

export interface SourceOut {
  id: string;
  url: string;
  title: string | null;
  publisher: string | null;
  retrieved_at: string;
  reachable: boolean;
  is_official: boolean;
  snippet: string | null;
}

/** Per-claim evidence reference — the trust contract. */
export interface ClaimEvidenceOut {
  claim: string;
  claim_type: "eligibility" | "deadline" | "document" | "amount" | "step" | "other";
  source_url: string;
  source_title: string | null;
  excerpt: string;
  retrieved_at: string;
  confidence: "confirmed" | "uncertain" | "unavailable";
  notes: string | null;
  freshness_days: number | null;
}

export interface ResearchResultOut {
  id: string;
  scholarship_name: string | null;
  provider: string | null;
  eligibility: string[];
  required_documents: string[];
  application_deadline: string | null;
  application_steps: string[];
  retrieved_at: string;
  verification_status: "verified" | "partial" | "unverified";
  confidence_notes: string | null;
  sources: SourceOut[];
}

export interface TranslationOut {
  id: string;
  language: Language;
  simplified_text: string;
  original_snippets: string[];
  source_ids: string[];
  created_at: string;
}

export interface ChecklistItem {
  title: string;
  detail: string;
  status: "todo" | "ready" | "missing" | "uncertain";
  source_url?: string | null;
}

export interface GuidanceOut {
  id: string;
  items: ChecklistItem[];
  missing_information: string[];
  unanswered_questions: string[];
  eligibility_assessment: string | null;
  uncertainty_warnings: string[];
  created_at: string;
}

export interface AgentExecutionOut {
  id: string;
  agent: "research" | "language" | "guidance";
  status: "started" | "success" | "error" | "skipped";
  started_at: string;
  finished_at: string | null;
  input_summary: string | null;
  output_summary: string | null;
  messages_exchanged: number;
  error_message: string | null;
  details: Record<string, unknown>;
}

export interface Workspace {
  question: {
    id: string;
    text: string;
    language: Language;
    category: Category;
    status: string;
    platform: string;
    channel: string;
    created_at: string;
    external_user: string | null;
    error_message: string | null;
  };
  research: ResearchResultOut | null;
  evidence: ClaimEvidenceOut[];
  conflicting_claims: string[];
  duplicate_sources: string[];
  translation: TranslationOut | null;
  guidance: GuidanceOut | null;
  executions: AgentExecutionOut[];
  approvals: { reviewer: string; action: string; note: string | null; at: string }[];
  audit: { actor: string; event: string; at: string; payload: Record<string, unknown> }[];
}

export interface DashboardData {
  recent_questions: QuestionList[];
  active_agent_runs: AgentExecutionOut[];
  pending_reviews: QuestionList[];
  completed_today: number;
  verification_summary: Record<string, number>;
  switch_status: {
    trust: Record<string, unknown>;
    bridge_enabled: boolean;
    mattermost_enabled: boolean;
  };
}

export interface EvaluationCase {
  id: string;
  question: string;
  language: string;
  expected_source_key: string | null;
  expected_verification: string;
  expected_min_eligibility: number;
  expected_min_documents: number;
  expected_evidence: boolean;
}

export interface EvaluationDataset {
  methodology: string;
  case_count: number;
  cases: EvaluationCase[];
}

export interface UnsupportedClaim {
  claim: string;
  claim_type: string;
  notes: string;
}
