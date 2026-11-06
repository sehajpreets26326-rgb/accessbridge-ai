import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send, Mic, MicOff, Loader2, ArrowRight } from "lucide-react";
import { api } from "../services/api";
import type { Language, Category } from "../types";

const SAMPLES = [
  "I am a girl student from India. Tell me about the AICTE Pragati scholarship for an engineering diploma.",
  "मैं एक छात्र हूँ, मुझे Ishan Uday scholarship के बारे में बताओ जो North East के लिए है।",
  "What scholarships can a West Bengal student apply for after class 12?",
];

export default function Ask() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [category, setCategory] = useState<Category>("scholarship");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim().length < 8) {
      setError("Please enter at least a sentence.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const q = await api.createQuestion({
        question_text: text.trim(),
        language,
        category,
        external_user: "web-user",
      });
      navigate(`/agents/${q.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit question.");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleVoice = () => {
    // Native browser speech recognition (Webkit only). Never auto-submits.
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setError("Voice input is not supported in this browser. Type your question instead.");
      return;
    }
    if (listening && recognition) {
      recognition.stop();
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = language === "hi" ? "hi-IN" : language === "pa" ? "pa-IN" : "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    const base = text ? text + " " : "";
    rec.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((r: any) => r[0].transcript)
        .join(" ");
      setText(base + transcript);
    };
    rec.onerror = (e: any) => {
      setError(`Voice input error: ${e.error}`);
      setListening(false);
    };
    rec.onend = () => setListening(false);
    rec.start();
    setRecognition(rec);
    setListening(true);
  };

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      <div className="notice text-slate uppercase tracking-wide">[Ask AccessBridge]</div>
      <h1 className="display text-3xl md:text-5xl text-ink mt-2">
        Ask about a scholarship or opportunity.
      </h1>
      <p className="text-slate mt-4 max-w-2xl leading-relaxed">
        Your question goes to the Research Agent, which retrieves official
        sources. The Language Agent simplifies and translates. The Guidance Agent
        builds a checklist. A human coordinator reviews before anything is delivered.
      </p>

      <form onSubmit={submit} className="card p-6 mt-8">
        <div className="flex items-center justify-between mb-3">
          <label htmlFor="q" className="text-sm font-medium text-ink">Your question</label>
          <div className="flex items-center gap-2 text-xs text-slate">
            <span className="nums">{text.length}/2000</span>
            <button
              type="button"
              onClick={toggleVoice}
              className={`btn-pill text-xs ${listening ? "btn-pill-primary" : "btn-pill-ghost"}`}
              title={listening ? "Stop dictation" : "Dictate (browser speech recognition)"}
            >
              {listening ? <MicOff size={13} /> : <Mic size={13} />}
              {listening ? "Stop" : "Dictate"}
            </button>
          </div>
        </div>
        <textarea
          id="q"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, 2000))}
          rows={5}
          className="w-full rounded-lg border border-ink/15 bg-cream/50 px-4 py-3 text-ink placeholder:text-slate-light focus:border-ink focus:bg-white outline-none transition-colors resize-y"
          placeholder="e.g. I am a girl student from India. Am I eligible for the AICTE Pragati scholarship for an engineering diploma? What documents do I need?"
        />

        <div className="grid sm:grid-cols-2 gap-4 mt-5">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
              className="mt-1.5 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink outline-none focus:border-ink"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as Category)}
              className="mt-1.5 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-ink outline-none focus:border-ink"
            >
              <option value="scholarship">Scholarship</option>
              <option value="admission">Admission</option>
              <option value="scheme">Government scheme</option>
              <option value="general">General</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 text-sm text-amber bg-amber-soft border border-amber/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between mt-6">
          <div className="text-xs text-slate">
            Voice dictation never auto-submits. Press Send when you're ready.
          </div>
          <button
            type="submit"
            disabled={submitting || text.trim().length < 8}
            className="btn-pill btn-pill-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {submitting ? "Submitting…" : "Send to agents"}
          </button>
        </div>
      </form>

      {/* Sample questions */}
      <div className="mt-10">
        <div className="notice text-slate uppercase tracking-wide mb-3">[Try one of these]</div>
        <div className="grid sm:grid-cols-3 gap-3">
          {SAMPLES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setText(s);
                setError(null);
              }}
              className="card p-4 text-left text-sm text-ink hover:border-ink/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="line-clamp-3">{s}</span>
                <ArrowRight size={13} className="text-slate mt-1 shrink-0" />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
