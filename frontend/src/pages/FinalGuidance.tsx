import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { ArrowRight, ExternalLink, ShieldCheck, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import type { Workspace, QuestionList } from "../types";
import StatusPill from "../components/StatusPill";
import { PageLoader, ErrorState } from "./Dashboard";

export default function FinalGuidance() {
  const { questionId: paramId } = useParams();
  const [activeId, setActiveId] = useState<string | undefined>(paramId);
  const [allQuestions, setAllQuestions] = useState<QuestionList[]>([]);
  const [data, setData] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    if (!activeId) return;
    (async () => {
      try {
        setData(await api.workspace(activeId));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [activeId]);

  if (loading && !data) return <PageLoader />;
  if (error && !data) return <ErrorState message={error} />;

  if (!activeId || !data) {
    return (
      <div className="max-w-editorial mx-auto px-6 py-16 text-center">
        <h2 className="display text-3xl text-ink">No final guidance generated yet</h2>
        <p className="text-slate text-sm mt-2">Questions approved by coordinators will appear here.</p>
        <Link to="/ask" className="btn-pill btn-pill-primary mt-6 inline-flex">Ask a question</Link>
      </div>
    );
  }

  const w = data;

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      {allQuestions.length > 1 && (
        <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2">
          <span className="text-xs text-slate uppercase font-semibold">Select guidance:</span>
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

      <div className="notice text-slate uppercase tracking-wide">[Final verified guidance]</div>
      <h1 className="display text-2xl md:text-4xl text-ink mt-2 break-words">{w.question.text}</h1>
      <div className="text-xs text-slate mt-2 nums">
        {w.question.external_user} · {w.question.language.toUpperCase()} · {new Date(w.question.created_at).toLocaleString()}
      </div>

      {/* Scholarship card */}
      {w.research && (
        <section className="card p-6 mt-8">
          <div className="grid sm:grid-cols-2 gap-4">
            <KV label="Scholarship" value={w.research.scholarship_name || "—"} />
            <KV label="Provider" value={w.research.provider || "—"} />
            <KV label="Deadline" value={w.research.application_deadline || "See official NSP calendar"} />
            <KV label="Review Verification">
              <span className="text-emerald-700 font-semibold flex items-center gap-1 text-sm">
                <CheckCircle2 size={15} /> 100% Source-Backed &amp; Approved
              </span>
            </KV>
          </div>
        </section>
      )}

      {/* Checklist items */}
      {w.guidance && (
        <section className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-ink">Personal Application Checklist</h2>
          <ol className="divide-y divide-ink/8 text-sm mt-4">
            {w.guidance.items.map((it, i) => (
              <li key={i} className="py-3 flex items-start gap-3">
                <span className="notice text-slate w-6 nums">{i + 1}.</span>
                <div>
                  <div className="text-ink font-semibold">{it.title}</div>
                  <div className="text-xs text-slate mt-0.5 leading-relaxed">{it.detail}</div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Simplified text */}
      {w.translation && (
        <section className="card p-6 mt-6">
          <h2 className="text-lg font-semibold text-ink">Simplified Guidance Summary</h2>
          <p className="text-sm text-ink leading-relaxed mt-3 whitespace-pre-wrap">{w.translation.simplified_text}</p>
        </section>
      )}
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
