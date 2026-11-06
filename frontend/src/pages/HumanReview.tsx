import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Check, X, RotateCw, Send, ArrowRight, RefreshCw } from "lucide-react";
import { api } from "../services/api";
import type { Workspace, QuestionList } from "../types";
import StatusPill from "../components/StatusPill";
import SourceCard from "../components/SourceCard";
import { PageLoader, ErrorState } from "./Dashboard";

export default function HumanReview() {
  const { questionId: paramId } = useParams();
  const [activeId, setActiveId] = useState<string | undefined>(paramId);
  const [pendingList, setPendingList] = useState<QuestionList[]>([]);
  const [data, setData] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("Coordinator #04");
  const [note, setNote] = useState("");
  const [secret, setSecret] = useState(localStorage.getItem("reviewSecret") || "");
  const [action, setAction] = useState<"approved" | "rejected" | "corrections_requested">("approved");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [delivering, setDelivering] = useState(false);
  const [delivered, setDelivered] = useState<string | null>(null);

  // If no paramId, find first question awaiting review or in list
  useEffect(() => {
    if (paramId) {
      setActiveId(paramId);
    } else {
      api.listQuestions()
        .then((qs) => {
          setPendingList(qs);
          const awaiting = qs.find((q) => q.status === "awaiting_review") || qs[0];
          if (awaiting) setActiveId(awaiting.id);
          else setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [paramId]);

  const load = async () => {
    if (!activeId) return;
    try {
      const d = await api.workspace(activeId);
      setData(d);
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

  const submitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeId) return;
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.review(activeId, {
        action,
        reviewer_name: reviewer,
        note: note || undefined,
        secret: secret || undefined,
      });
      setResult(`Saved: ${res.action}`);
      await load();
    } catch (err) {
      setResult(err instanceof Error ? err.message : "Failed to record review.");
    } finally {
      setSubmitting(false);
    }
  };

  const deliverToRoom = async () => {
    if (!activeId) return;
    setDelivering(true);
    try {
      const res = await api.deliver(activeId);
      setDelivered(`Delivered: ${res.delivered}`);
      await load();
    } catch (err) {
      setDelivered(err instanceof Error ? err.message : "Delivery failed.");
    } finally {
      setDelivering(false);
    }
  };

  if (loading && !data) return <PageLoader />;
  if (error && !data) return <ErrorState message={error} />;

  if (!activeId || !data) {
    return (
      <div className="max-w-editorial mx-auto px-6 py-16 text-center">
        <h2 className="display text-3xl text-ink">No requests pending review</h2>
        <p className="text-slate text-sm mt-2">All questions have been reviewed or none are currently queued.</p>
        <Link to="/ask" className="btn-pill btn-pill-primary mt-6 inline-flex">Submit a new request</Link>
      </div>
    );
  }

  const w = data;

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      {pendingList.length > 1 && (
        <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2">
          <span className="text-xs text-slate uppercase font-semibold">Review queue:</span>
          {pendingList.map((q) => (
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
        <div>
          <div className="notice text-slate uppercase tracking-wide">[Coordinator review desk]</div>
          <h1 className="display text-2xl md:text-4xl text-ink mt-2 break-words">{w.question.text}</h1>
          <div className="text-xs text-slate mt-2 nums">
            {w.question.external_user} · {w.question.platform} · #{w.question.channel} ·{" "}
            {new Date(w.question.created_at).toLocaleString()}
          </div>
        </div>
        <StatusPill status={w.question.status} />
      </div>

      {/* Review Form Card */}
      <section className="card p-6 mt-8 border-2 border-ink/20">
        <h2 className="text-lg font-semibold text-ink">Record coordinator decision</h2>
        <p className="text-xs text-slate mt-0.5">
          Final guidance is only sent to the student channel after explicit coordinator approval.
        </p>

        <form onSubmit={submitReview} className="mt-5 space-y-4">
          <div className="grid sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => setAction("approved")}
              className={`p-3 rounded-lg border text-left transition ${
                action === "approved" ? "border-emerald-600 bg-emerald-50 text-emerald-950 font-bold" : "border-ink/15 bg-white text-slate"
              }`}
            >
              <div className="flex items-center gap-2"><Check size={14} className="text-emerald-600" /> Approve</div>
              <div className="text-[11px] text-slate mt-1 font-normal">Delivers guidance to the student</div>
            </button>
            <button
              type="button"
              onClick={() => setAction("corrections_requested")}
              className={`p-3 rounded-lg border text-left transition ${
                action === "corrections_requested" ? "border-amber-600 bg-amber-50 text-amber-950 font-bold" : "border-ink/15 bg-white text-slate"
              }`}
            >
              <div className="flex items-center gap-2"><RefreshCw size={14} className="text-amber-600" /> Corrections</div>
              <div className="text-[11px] text-slate mt-1 font-normal">Requests another pass from agents</div>
            </button>
            <button
              type="button"
              onClick={() => setAction("rejected")}
              className={`p-3 rounded-lg border text-left transition ${
                action === "rejected" ? "border-rose-600 bg-rose-50 text-rose-950 font-bold" : "border-ink/15 bg-white text-slate"
              }`}
            >
              <div className="flex items-center gap-2"><X size={14} className="text-rose-600" /> Reject</div>
              <div className="text-[11px] text-slate mt-1 font-normal">Invalid or unsupported request</div>
            </button>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs uppercase tracking-wide text-slate">Reviewer name</label>
              <input
                type="text"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                className="mt-1 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wide text-slate">Notes / Verification basis</label>
              <input
                type="text"
                placeholder="e.g. Official criteria confirmed on AICTE portal."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="mt-1 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink"
              />
            </div>
          </div>

          {result && (
            <div className="text-xs p-2.5 rounded bg-cream-deep border border-ink/10 text-ink">
              {result}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate">Audit logs will record this action permanently.</span>
            <button
              type="submit"
              disabled={submitting}
              className="btn-pill btn-pill-primary text-xs"
            >
              {submitting ? "Saving..." : "Submit Review Decision"}
            </button>
          </div>
        </form>

        {w.question.status === "approved" && (
          <div className="mt-6 pt-5 border-t border-ink/10 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-emerald-800">Approved by coordinator</div>
              <div className="text-xs text-slate">Ready to post final guidance to student communication room.</div>
            </div>
            <button
              onClick={deliverToRoom}
              disabled={delivering}
              className="btn-pill bg-emerald-700 text-white hover:bg-emerald-800 text-xs flex items-center gap-1.5"
            >
              <Send size={13} />
              {delivering ? "Posting..." : "Dispatch Final Guidance to Room"}
            </button>
          </div>
        )}
      </section>

      {/* Research Sources Preview */}
      {w.research && (
        <section className="card p-5 mt-8">
          <h3 className="font-semibold text-ink text-sm mb-3">Extracted Sources Checked by Agents</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {w.research.sources.map((s) => (
              <SourceCard key={s.id} source={s} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
