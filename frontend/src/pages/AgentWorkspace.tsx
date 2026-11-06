import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Search, Languages, ClipboardCheck, Cpu, ArrowRight, RotateCw, ExternalLink, AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import type { Workspace, AgentExecutionOut, ClaimEvidenceOut, QuestionList } from "../types";
import StatusPill from "../components/StatusPill";
import SourceCard from "../components/SourceCard";
import { PageLoader, ErrorState } from "./Dashboard";

export default function AgentWorkspace() {
  const { questionId: paramId } = useParams();
  const [activeId, setActiveId] = useState<string | undefined>(paramId);
  const [allQuestions, setAllQuestions] = useState<QuestionList[]>([]);
  const [data, setData] = useState<Workspace | null>(null);
  const [evidence, setEvidence] = useState<ClaimEvidenceOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // If no paramId provided in route, load the list of questions and pick the first one
  useEffect(() => {
    if (paramId) {
      setActiveId(paramId);
    } else {
      api.listQuestions()
        .then((qs) => {
          setAllQuestions(qs);
          if (qs.length > 0) setActiveId(qs[0].id);
          else setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [paramId]);

  const load = async () => {
    if (!activeId) return;
    try {
      const [d, ev] = await Promise.all([
        api.workspace(activeId),
        api.getEvidence(activeId).catch(() => []),
      ]);
      setData(d);
      setEvidence(ev);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeId) {
      load();
      const t = setInterval(load, 3000);
      return () => clearInterval(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  if (loading && !data) return <PageLoader />;
  if (error && !data) return <ErrorState message={error} />;
  
  if (!activeId || !data) {
    return (
      <div className="max-w-editorial mx-auto px-6 py-16 text-center">
        <h2 className="display text-3xl text-ink">No active agent traces yet</h2>
        <p className="text-slate text-sm mt-2">Submit a question to watch Fetch.ai agents execute live.</p>
        <Link to="/ask" className="btn-pill btn-pill-primary mt-6 inline-flex">Ask a question</Link>
      </div>
    );
  }

  const w = data;

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      {/* Switcher if multiple questions exist */}
      {allQuestions.length > 1 && (
        <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2">
          <span className="text-xs text-slate uppercase font-semibold">Select trace:</span>
          {allQuestions.map((q) => (
            <button
              key={q.id}
              onClick={() => setActiveId(q.id)}
              className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition ${
                activeId === q.id ? "bg-slate-900 text-white" : "bg-white border border-ink/10 text-slate hover:text-ink"
              }`}
            >
              {q.question_text.slice(0, 32)}...
            </button>
          ))}
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="notice text-slate uppercase tracking-wide">[Agent workspace]</div>
          <h1 className="display text-2xl md:text-4xl text-ink mt-2 break-words">
            {w.question.text}
          </h1>
          <div className="text-xs text-slate mt-2 nums">
            {w.question.external_user || "anonymous"} · {w.question.platform} · #{w.question.channel} ·{" "}
            {new Date(w.question.created_at).toLocaleString()}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <StatusPill status={w.question.status} />
          <button onClick={load} className="btn-pill btn-pill-ghost text-xs">
            <RotateCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Three agent cards */}
      <div className="grid md:grid-cols-3 gap-3 mt-8">
        <AgentCard
          name="Research Agent"
          icon={<Search size={16} />}
          exec={w.executions.find((e) => e.agent === "research")}
          input={w.question.text}
          output={
            w.research
              ? `${w.research.scholarship_name || "no match"} · ${w.research.sources.length} source(s) · ${w.research.verification_status}`
              : null
          }
        />
        <AgentCard
          name="Language Agent"
          icon={<Languages size={16} />}
          exec={w.executions.find((e) => e.agent === "language")}
          input={w.question.language}
          output={
            w.translation
              ? `${w.translation.language} · ${w.translation.simplified_text.length} chars`
              : null
          }
        />
        <AgentCard
          name="Guidance Agent"
          icon={<ClipboardCheck size={16} />}
          exec={w.executions.find((e) => e.agent === "guidance")}
          input="research + translation"
          output={
            w.guidance
              ? `${w.guidance.items.length} checklist items · ${w.guidance.missing_information.length} missing`
              : null
          }
        />
      </div>

      {/* Research output */}
      {w.research && (
        <section className="mt-10">
          <SectionTitle title="Research" subtitle={`Retrieved ${new Date(w.research.retrieved_at).toLocaleString()}`} />
          <div className="card p-5">
            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <KV label="Scholarship" value={w.research.scholarship_name || "—"} />
              <KV label="Provider" value={w.research.provider || "—"} />
              <KV label="Deadline" value={w.research.application_deadline || "Not stated in source"} />
              <KV label="Verification">
                <StatusPill status={w.research.verification_status} />
              </KV>
            </div>
            {w.research.confidence_notes && (
              <p className="text-sm text-amber mt-3 bg-amber-soft/60 border border-amber/20 rounded px-3 py-2">
                {w.research.confidence_notes}
              </p>
            )}
            {w.research.eligibility.length > 0 && <List label="Eligibility" items={w.research.eligibility} />}
            {w.research.required_documents.length > 0 && (
              <List label="Required documents" items={w.research.required_documents} />
            )}
            {w.research.application_steps.length > 0 && (
              <List label="Application steps" items={w.research.application_steps} />
            )}

            <div className="hairline mt-6 pt-5">
              <div className="text-xs uppercase tracking-wide text-slate mb-3">
                Official sources ({w.research.sources.length})
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {w.research.sources.map((s) => (
                  <SourceCard key={s.id} source={s} />
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Evidence Inspector */}
      {evidence.length > 0 && (
        <section className="mt-10">
          <SectionTitle
            title="Evidence inspector"
            subtitle="Every extracted claim tied to its source excerpt and freshness."
          />
          <div className="card divide-y divide-ink/8">
            {evidence.map((ev, i) => (
              <div key={i} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-sm font-medium text-ink">{ev.claim}</div>
                  <span className="notice text-xs uppercase text-slate shrink-0">{ev.claim_type}</span>
                </div>
                {ev.excerpt && (
                  <blockquote className="mt-2 text-xs text-slate-deep bg-cream-deep/60 border-l-2 border-ink/20 pl-3 py-1.5 italic">
                    "{ev.excerpt}"
                  </blockquote>
                )}
                <div className="mt-2 flex items-center justify-between text-xs text-slate">
                  <a
                    href={ev.source_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="link-ink inline-flex items-center gap-1 max-w-[70%] truncate"
                  >
                    {ev.source_title || ev.source_url} <ExternalLink size={10} />
                  </a>
                  <span className="nums">
                    {ev.freshness_days != null
                      ? ev.freshness_days < 1
                        ? "Retrieved today"
                        : `${Math.round(ev.freshness_days)}d old`
                      : "Timestamped"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Language output */}
      {w.translation && (
        <section className="mt-10">
          <SectionTitle
            title={`Translation (${w.translation.language.toUpperCase()})`}
            subtitle="Simplified explanation with verbatim official clauses preserved."
          />
          <div className="card p-5">
            <p className="text-ink leading-relaxed whitespace-pre-wrap">{w.translation.simplified_text}</p>
            {w.translation.original_snippets.length > 0 && (
              <div className="hairline mt-5 pt-4">
                <div className="text-xs uppercase tracking-wide text-slate mb-2">Preserved original clauses</div>
                <ul className="text-xs text-slate space-y-1">
                  {w.translation.original_snippets.map((sn, i) => (
                    <li key={i} className="font-mono bg-cream-deep/60 px-2 py-1 rounded">
                      "{sn}"
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Guidance output */}
      {w.guidance && (
        <section className="mt-10">
          <SectionTitle title="Application checklist" subtitle="Synthesised by the Guidance Agent." />
          <div className="card p-5">
            {w.guidance.eligibility_assessment && (
              <p className="text-sm text-ink mb-4 pb-4 border-b border-ink/8 leading-relaxed">
                <span className="font-medium">Assessment: </span>
                {w.guidance.eligibility_assessment}
              </p>
            )}
            <ol className="divide-y divide-ink/8 text-sm">
              {w.guidance.items.map((it, i) => (
                <li key={i} className="py-2.5 flex items-start gap-3">
                  <span className="notice text-slate w-6 nums">{i + 1}.</span>
                  <div className="flex-1">
                    <div className="text-ink font-medium">{it.title}</div>
                    <div className="text-xs text-slate mt-0.5">{it.detail}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {/* Review CTA */}
      {w.question.status === "awaiting_review" && (
        <div className="mt-10 card p-5 flex items-center justify-between">
          <div>
            <div className="text-ink font-medium">Ready for human review</div>
            <div className="text-sm text-slate">A coordinator must approve before final guidance is delivered.</div>
          </div>
          <Link to={`/review/${w.question.id}`} className="btn-pill btn-pill-primary">
            Open review <ArrowRight size={14} />
          </Link>
        </div>
      )}
      {(w.question.status === "approved" || w.question.status === "delivered") && (
        <div className="mt-10 card p-5 flex items-center justify-between">
          <div>
            <div className="text-ink font-medium">Final guidance</div>
            <div className="text-sm text-slate">Read the delivered answer.</div>
          </div>
          <Link to={`/guidance/${w.question.id}`} className="btn-pill btn-pill-primary">
            View final guidance <ArrowRight size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}

function AgentCard({ name, icon, exec, input, output }: { name: string; icon: React.ReactNode; exec?: AgentExecutionOut; input?: string; output?: string | null }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink font-medium">
          {icon} {name}
        </div>
        <Cpu size={14} className="text-slate" />
      </div>
      <div className="mt-3 text-xs text-slate">
        <div className="flex items-center justify-between">
          <span>Status</span>
          {exec ? <StatusPill status={exec.status} /> : <span className="text-slate-light">queued</span>}
        </div>
        {input && (
          <div className="mt-2">
            <span className="text-slate-light">input: </span>
            <span className="text-ink truncate">{input}</span>
          </div>
        )}
        {output && (
          <div className="mt-1">
            <span className="text-slate-light">output: </span>
            <span className="text-ink">{output}</span>
          </div>
        )}
        {exec?.error_message && (
          <div className="mt-2 text-amber">{exec.error_message}</div>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      {subtitle && <p className="text-sm text-slate mt-0.5 nums">{subtitle}</p>}
    </div>
  );
}

function KV({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-slate mb-1">{label}</div>
      <div className="text-ink">{children ?? value}</div>
    </div>
  );
}

function List({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="mt-4">
      <div className="text-xs uppercase tracking-wide text-slate mb-1.5">{label}</div>
      <ul className="text-sm text-ink space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="text-slate mt-0.5">·</span>
            <span className="leading-relaxed">{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
