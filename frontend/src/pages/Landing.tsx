import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Send,
  Search,
  Languages,
  ClipboardCheck,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  MessageSquare,
} from "lucide-react";
import { BarField, DitherPortrait, Notice } from "../components/Motifs";
import UserIconBackground from "../components/UserIconBackground";

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="max-w-editorial mx-auto px-6 pt-16 md:pt-24 pb-16 md:pb-24 grid md:grid-cols-12 gap-8 md:gap-12 items-center">
          <div className="md:col-span-7">
            <div className="notice text-slate uppercase tracking-wide mb-6">
              [AccessBridge · public-interest AI]
            </div>
            <h1 className="display text-[2.75rem] md:text-[4.25rem] text-ink leading-tight">
              Essential information,<br />
              understandable to everyone.
            </h1>
            <p className="text-slate text-lg mt-6 max-w-xl leading-relaxed">
              AccessBridge turns complicated scholarship and educational-opportunity
              information into source-backed guidance — researched by AI agents,
              simplified and translated, and reviewed by a human coordinator before
              it reaches a student.
            </p>
            <div className="flex flex-wrap items-center gap-3 mt-8">
              <Link to="/chat-demo" className="btn-pill btn-pill-primary flex items-center gap-1.5 shadow-sm">
                <MessageSquare size={15} /> Open Live Chat Simulator
              </Link>
              <Link to="/ask" className="btn-pill btn-pill-ghost border border-ink/15">
                <Send size={15} /> Ask a question
              </Link>
              <Link to="/dashboard" className="btn-pill btn-pill-ghost">
                View dashboard <ArrowRight size={14} />
              </Link>
            </div>
            <div className="hairline mt-10 pt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-verified" /> English · हिन्दी · ਪੰਜਾਬੀ
              </span>
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-verified" /> Telegram · Discord · Switch
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={13} className="text-verified" /> 3 Fetch.ai uAgents
              </span>
            </div>
          </div>
          <div className="md:col-span-5">
            {/* Custom Interactive User Hologram Artwork */}
            <div className="relative shadow-xl rounded-2xl overflow-hidden border border-ink/20">
              <UserIconBackground className="w-full aspect-[4/3] md:aspect-[4/5]" />
              <div className="absolute bottom-3 left-3 right-3 bg-slate-950/80 backdrop-blur-md p-3 rounded-xl border border-cyan-500/30 text-white text-xs">
                <div className="flex items-center justify-between font-semibold text-cyan-300">
                  <span>Student Guidance Pipeline</span>
                  <span className="text-[10px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/40">● Live Connected</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-1">
                  Telegram &amp; Discord chatrooms routed via Switch Bridge to Fetch.ai agents.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Chatroom Showcase Banner */}
      <section className="bg-slate-900 text-white py-12 border-y border-cyan-500/20">
        <div className="max-w-editorial mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="inline-block px-2.5 py-0.5 rounded text-[11px] font-semibold tracking-wider uppercase bg-cyan-950 text-cyan-300 border border-cyan-700/50 mb-2">
              New: Multi-Platform Transport
            </div>
            <h2 className="text-2xl font-bold">Try the Interactive Chat Simulator</h2>
            <p className="text-slate-300 text-sm mt-1 max-w-xl">
              See exactly how students ask questions on Telegram or Discord, how agents process in real time, and how coordinators approve answers.
            </p>
          </div>
          <Link to="/chat-demo" className="btn-pill bg-cyan-400 text-slate-950 hover:bg-cyan-300 font-bold text-sm px-6 py-3 whitespace-nowrap shadow-lg">
            Launch Chat Simulator →
          </Link>
        </div>
      </section>

      {/* Workflow Engine */}
      <section className="bg-cream-deep border-b border-ink/10">
        <div className="max-w-editorial mx-auto px-6 py-16 md:py-24 grid md:grid-cols-12 gap-10">
          <div className="md:col-span-5">
            <div className="notice text-slate uppercase tracking-wide mb-4">[01 · Workflow Engine]</div>
            <h2 className="display text-3xl md:text-5xl text-ink">A team of agents, not a single chatbot.</h2>
            <p className="text-slate mt-5 leading-relaxed text-sm">
              Three independent Fetch.ai uAgents — Research, Language, and Guidance —
              each own one job and exchange structured Pydantic messages through an
              orchestrator. A human coordinator reviews before anything reaches the
              student. No agent invents information.
            </p>
          </div>
          <div className="md:col-span-7 md:pl-6">
            <BarField seed={7} count={80} className="w-full" />
            <div className="mt-6 grid sm:grid-cols-3 gap-3">
              <AgentRoleCard
                index="01"
                title="Research"
                icon={<Search size={16} />}
                body="Retrieves official sources, extracts eligibility, documents, deadlines."
              />
              <AgentRoleCard
                index="02"
                title="Language"
                icon={<Languages size={16} />}
                body="Simplifies official language and translates to English, Hindi or Punjabi."
              />
              <AgentRoleCard
                index="03"
                title="Guidance"
                icon={<ClipboardCheck size={16} />}
                body="Builds a personal application checklist and flags missing information."
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function AgentRoleCard({ index, title, icon, body }: { index: string; title: string; icon: React.ReactNode; body: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <span className="notice text-slate">{index}</span>
        <span className="text-ink">{icon}</span>
      </div>
      <div className="mt-3 text-ink font-medium">{title}</div>
      <p className="text-xs text-slate mt-1 leading-relaxed">{body}</p>
    </div>
  );
}
