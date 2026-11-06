import { Link } from "react-router-dom";
import { Inbox, Cpu, ClipboardCheck, CheckCircle2, ShieldCheck, ArrowRight } from "lucide-react";
import { usePoll } from "../hooks/usePoll";
import { api } from "../services/api";
import type { DashboardData } from "../types";
import StatusPill from "../components/StatusPill";

export default function Dashboard() {
  const { data, loading, error } = usePoll<DashboardData>(api.dashboard, { intervalMs: 4000 });

  if (loading && !data) return <PageLoader />;
  if (error && !data) return <ErrorState message={error} />;

  const d = data!;
  const trust = d.switch_status.trust as Record<string, unknown>;

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      <Header />

      {/* Status strip */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-8">
        <StatCard label="Recent questions" value={d.recent_questions.length} icon={<Inbox size={16} />} />
        <StatCard label="Active agent runs" value={d.active_agent_runs.length} icon={<Cpu size={16} />} />
        <StatCard label="Pending reviews" value={d.pending_reviews.length} icon={<ClipboardCheck size={16} />} />
        <StatCard label="Completed today" value={d.completed_today} icon={<CheckCircle2 size={16} />} />
      </div>

      {/* Switch status */}
      <section className="card mt-6 p-5">
        <div className="flex items-center gap-2 text-ink font-medium">
          <ShieldCheck size={16} /> Switch integration status
        </div>
        <div className="grid sm:grid-cols-3 gap-4 mt-4 text-sm">
          <Field label="Switch Trust guardrails">
            <span className={trust?.configured ? "text-verified" : "text-amber"}>
              {trust?.enabled ? (trust?.configured ? "Configured" : "Pass-through (set SWITCH_TRUST_API_KEY)") : "Disabled"}
            </span>
          </Field>
          <Field label="SDK version">
            <span className="nums text-slate">{String(trust?.sdk_version ?? "—")}</span>
          </Field>
          <Field label="Gateway">
            <span className="text-slate break-all">{String(trust?.gateway_url ?? "—")}</span>
          </Field>
          <Field label="Agent bridge endpoint">
            <span className={d.switch_status.bridge_enabled ? "text-verified" : "text-amber"}>
              {d.switch_status.bridge_enabled ? "Listening at /switch/bridge" : "Off"}
            </span>
          </Field>
          <Field label="Mattermost transport">
            <span className={d.switch_status.mattermost_enabled ? "text-verified" : "text-amber"}>
              {d.switch_status.mattermost_enabled ? "Configured" : "Not configured"}
            </span>
          </Field>
          <Field label="Verification summary">
            <span className="text-slate nums">
              {Object.entries(d.verification_summary)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ") || "—"}
            </span>
          </Field>
        </div>
      </section>

      {/* Recent questions */}
      <section className="mt-10">
        <SectionTitle title="Recent guidance requests" subtitle="Every row is a real question handled by the agents." />
        {d.recent_questions.length === 0 ? (
          <EmptyState message="No questions yet. Ask one to see it here." cta />
        ) : (
          <div className="card divide-y divide-ink/8">
            {d.recent_questions.map((q) => (
              <Link
                key={q.id}
                to={`/agents/${q.id}`}
                className="flex items-center gap-4 p-4 hover:bg-cream-deep/40 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-ink truncate">{q.question_text}</div>
                  <div className="text-xs text-slate mt-0.5 nums">
                    {q.external_user || "anonymous"} · {q.language} · {new Date(q.created_at).toLocaleString()}
                  </div>
                </div>
                <StatusPill status={q.status} />
                <ArrowRight size={14} className="text-slate shrink-0" />
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Pending reviews */}
      {d.pending_reviews.length > 0 && (
        <section className="mt-10">
          <SectionTitle title="Pending human review" subtitle="Awaiting a coordinator's decision." />
          <div className="card divide-y divide-ink/8">
            {d.pending_reviews.map((q) => (
              <Link
                key={q.id}
                to={`/review/${q.id}`}
                className="flex items-center gap-4 p-4 hover:bg-cream-deep/40 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-ink truncate">{q.question_text}</div>
                  <div className="text-xs text-slate mt-0.5 nums">
                    {q.external_user || "anonymous"} · {new Date(q.created_at).toLocaleString()}
                  </div>
                </div>
                <StatusPill status={q.status} />
                <ArrowRight size={14} className="text-slate shrink-0" />
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Header() {
  return (
    <div className="flex items-end justify-between">
      <div>
        <div className="notice text-slate uppercase tracking-wide">[Dashboard]</div>
        <h1 className="display text-3xl md:text-4xl text-ink mt-2">Live workflow overview</h1>
      </div>
      <Link to="/ask" className="btn-pill btn-pill-primary text-sm">New question</Link>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-slate">
        <span className="text-xs uppercase tracking-wide">{label}</span>
        <span>{icon}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold text-ink nums">{value}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-slate uppercase tracking-wide mb-1">{label}</div>
      <div className="text-ink">{children}</div>
    </div>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      {subtitle && <p className="text-sm text-slate mt-0.5">{subtitle}</p>}
    </div>
  );
}

function EmptyState({ message, cta }: { message: string; cta?: boolean }) {
  return (
    <div className="card p-10 text-center">
      <p className="text-slate">{message}</p>
      {cta && (
        <Link to="/ask" className="btn-pill btn-pill-primary mt-4 inline-flex">
          Ask a question
        </Link>
      )}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="max-w-editorial mx-auto px-6 py-20 text-center text-slate">
      <div className="notice uppercase tracking-wide">[Loading live data…]</div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-editorial mx-auto px-6 py-20 text-center">
      <div className="notice text-amber uppercase tracking-wide">[Backend unreachable]</div>
      <p className="text-slate mt-2 text-sm">{message}</p>
      <p className="text-slate mt-1 text-xs">
        Start the backend with <code className="notice bg-cream-deep px-1.5 py-0.5 rounded">uvicorn backend.app.main:app --port 8000</code>
      </p>
    </div>
  );
}
