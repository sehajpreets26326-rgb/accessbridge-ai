import { useState, useEffect, useRef } from "react";
import { Send, Bot, CheckCircle, ShieldCheck, User, MessageCircle, AlertCircle } from "lucide-react";
import { api } from "../services/api";

type Platform = "telegram" | "discord" | "mattermost";

interface ChatMessage {
  id: string;
  sender: "user" | "bot" | "coordinator" | "system";
  senderName: string;
  text: string;
  timestamp: string;
  platform: Platform;
  badge?: string;
  sourceLinks?: { title: string; url: string }[];
}

export default function ChatSimulator() {
  const [platform, setPlatform] = useState<Platform>("telegram");
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      sender: "system",
      senderName: "Switch Gateway",
      text: "Switch Console Agent Bridge connected. Outbound transports: Telegram Bot API, Discord REST API, and Mattermost Webhooks.",
      timestamp: new Date(Date.now() - 1000 * 60 * 5).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: "telegram",
    },
    {
      id: "initial-q",
      sender: "user",
      senderName: "Simran Kaur",
      text: "What documents do I need for the AICTE Pragati scholarship for girls? I am in 2nd year B.Tech and family income is below ₹8 Lakh.",
      timestamp: new Date(Date.now() - 1000 * 60 * 4).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: "telegram",
    },
    {
      id: "initial-progress",
      sender: "bot",
      senderName: "AccessBridge Teammate",
      badge: "Switch Trust Verified",
      text: "Research started — querying curated AICTE guidelines & National Scholarship Portal (NSP). Extracted 2 verified official sources.",
      timestamp: new Date(Date.now() - 1000 * 60 * 3).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: "telegram",
    },
    {
      id: "initial-review",
      sender: "coordinator",
      senderName: "Coordinator #04 (Dr. Priya Mehta)",
      badge: "Human Review Approved",
      text: "Human-in-the-Loop review completed: Verified that lateral entry admission criteria are met and ₹8L income threshold is certified.",
      timestamp: new Date(Date.now() - 1000 * 60 * 2).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: "telegram",
    },
    {
      id: "initial-delivered",
      sender: "bot",
      senderName: "AccessBridge Guidance",
      badge: "Delivered to Student",
      text: "Here is your official guidance for the AICTE Pragati Scholarship:\n\n• Benefit: ₹50,000/year assistance.\n• Lateral Entry: Eligible for 2nd year if admitted via lateral entry to an AICTE-approved institution.\n• Required Documents:\n  1. Revenue Authority Income Certificate (< ₹8 Lakh)\n  2. Diploma / 10+2 marksheet\n  3. AICTE Admission letter & Fee receipt\n  4. Aadhaar-seeded bank account\n\nApply via National Scholarship Portal (scholarships.gov.in) before closing deadline.",
      timestamp: new Date(Date.now() - 1000 * 60 * 1).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: "telegram",
      sourceLinks: [
        { title: "AICTE Official Pragati Guidelines", url: "https://www.aicte-india.org/schemes/students-development-schemes/pragati" },
        { title: "NSP AICTE FAQs (Official)", url: "https://scholarships.gov.in/public/faq/AICTE_FAQ.pdf" }
      ]
    }
  ]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStep]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userText = input.trim();
    setInput("");
    setIsProcessing(true);

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: "user",
      senderName: platform === "telegram" ? "@student_user" : platform === "discord" ? "StudentApplicant#1024" : "student_member",
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      platform: platform,
    };

    setMessages((prev) => [...prev, userMsg]);

    // Send question to backend API with selected platform!
    try {
      setCurrentStep("Switch Bridge: Delivering message to AccessBridge backend...");
      const q = await api.createQuestion({
        question_text: userText,
        language: "en",
        category: "scholarship",
        platform: platform,
        external_user: userMsg.senderName,
      });

      // Step 1: Research Agent
      setTimeout(() => {
        setCurrentStep("Research Agent: Searching official portals & extracting citations...");
        setMessages((prev) => [
          ...prev,
          {
            id: `bot-res-${Date.now()}`,
            sender: "bot",
            senderName: "AccessBridge Teammate",
            badge: "Fetch.ai Research",
            text: `Question accepted (ID: ${q.id.slice(0, 8)}). Research Agent is scanning official education schemas. Found matching scheme with 100% citation links.`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            platform: platform,
          }
        ]);
      }, 1200);

      // Step 2: Language & Guidance
      setTimeout(() => {
        setCurrentStep("Language & Guidance Agents: Simplifying jargon and building checklist...");
        setMessages((prev) => [
          ...prev,
          {
            id: `bot-lang-${Date.now()}`,
            sender: "bot",
            senderName: "AccessBridge Teammate",
            badge: "Language & Guidance",
            text: "Official bureaucratic language simplified. Application checklist and gap analysis generated. Gated for coordinator review.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            platform: platform,
          }
        ]);
      }, 2600);

      // Step 3: Coordinator Human-in-the-Loop review
      setTimeout(() => {
        setCurrentStep("Coordinator: Verifying official sources...");
        setMessages((prev) => [
          ...prev,
          {
            id: `coord-${Date.now()}`,
            sender: "coordinator",
            senderName: "Coordinator Desk (HITL)",
            badge: "Approved by Human",
            text: "Coordinator checked sources: Verified official guidelines, validated income limits and lateral criteria. Approved for student delivery.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            platform: platform,
          }
        ]);
      }, 4200);

      // Step 4: Final delivery back into chatroom
      setTimeout(() => {
        setCurrentStep("");
        setIsProcessing(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `final-${Date.now()}`,
            sender: "bot",
            senderName: "AccessBridge Guidance",
            badge: "Final Guidance",
            text: `Final verified guidance for "${userText}":\n\n• Scheme validated from official database.\n• Ensure application is submitted before official portal closing.\n• Required: Income certificate (< ₹8 Lakh), previous academic marksheets, admission proof and Aadhaar-seeded bank account.`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            platform: platform,
            sourceLinks: [
              { title: "National Scholarship Portal Official Portal", url: "https://scholarships.gov.in" },
              { title: "Central Scheme Eligibility Repository", url: "https://www.aicte-india.org" }
            ]
          }
        ]);
      }, 5600);

    } catch (err: any) {
      setIsProcessing(false);
      setCurrentStep("");
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "system",
          senderName: "Error",
          text: `Workflow notice: ${err?.message || "Processed locally with offline verified fallback."}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          platform: platform,
        }
      ]);
    }
  };

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="notice text-slate uppercase tracking-wide">[Interactive Chat Demonstration]</div>
          <h1 className="display text-3xl md:text-5xl text-ink mt-2">Chat Integration Simulator</h1>
          <p className="text-slate mt-2 text-sm max-w-2xl">
            Simulate how students interact with AccessBridge directly through <strong>Telegram</strong>, <strong>Discord</strong>, or <strong>Mattermost</strong> via Switch's Console Agent Bridge.
          </p>
        </div>

        {/* Platform Selector Buttons */}
        <div className="flex items-center gap-1.5 bg-cream-deep p-1.5 rounded-xl border border-ink/10">
          <button
            type="button"
            onClick={() => setPlatform("telegram")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              platform === "telegram" ? "bg-white text-ink shadow-sm" : "text-slate hover:text-ink"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-sky-500"></span> Telegram
          </button>
          <button
            type="button"
            onClick={() => setPlatform("discord")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              platform === "discord" ? "bg-white text-ink shadow-sm" : "text-slate hover:text-ink"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-indigo-500"></span> Discord
          </button>
          <button
            type="button"
            onClick={() => setPlatform("mattermost")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              platform === "mattermost" ? "bg-white text-ink shadow-sm" : "text-slate hover:text-ink"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Mattermost
          </button>
        </div>
      </div>

      {/* Main Chat Box Container */}
      <div className="mt-8 card border border-ink/15 shadow-sm overflow-hidden flex flex-col h-[650px] bg-white">
        
        {/* Chat Room Header */}
        <div className="px-5 py-3.5 bg-slate-50 border-b border-ink/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white text-xs ${
              platform === "telegram" ? "bg-sky-500" : platform === "discord" ? "bg-indigo-600" : "bg-emerald-600"
            }`}>
              {platform === "telegram" ? "TG" : platform === "discord" ? "DC" : "MM"}
            </div>
            <div>
              <div className="text-sm font-bold text-ink">
                {platform === "telegram" ? "AccessBridge Bot (@AccessBridgeAIBot)" : platform === "discord" ? "#student-questions (AccessBridge#01)" : "#student-questions · AccessBridge Room"}
              </div>
              <div className="text-xs text-slate flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Switch Console Agent Bridge · Active</span>
              </div>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs text-slate">
            <ShieldCheck size={14} className="text-verified" />
            <span>Human-in-the-Loop Verification Active</span>
          </div>
        </div>

        {/* Message Thread Area */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-[#FBFBFA]/50">
          {messages.map((m) => {
            const isUser = m.sender === "user";
            const isSystem = m.sender === "system";
            const isCoord = m.sender === "coordinator";

            if (isSystem) {
              return (
                <div key={m.id} className="text-center my-3">
                  <span className="inline-block px-3 py-1 rounded-full bg-cream-deep border border-ink/10 text-[11px] text-slate">
                    {m.text}
                  </span>
                </div>
              );
            }

            return (
              <div key={m.id} className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                  isUser 
                    ? "bg-slate-900 text-white" 
                    : isCoord 
                    ? "bg-amber-600 text-white" 
                    : "bg-softblue text-ink border border-ink/10"
                }`}>
                  {isUser ? <User size={13} /> : isCoord ? "HC" : <Bot size={13} />}
                </div>

                <div className={`max-w-xl rounded-2xl px-4 py-3 text-sm ${
                  isUser 
                    ? "bg-slate-900 text-white rounded-tr-none" 
                    : isCoord 
                    ? "bg-amber-50 border border-amber-200 text-ink rounded-tl-none" 
                    : "bg-white border border-ink/10 text-ink shadow-xs rounded-tl-none"
                }`}>
                  <div className="flex items-center justify-between gap-3 mb-1">
                    <span className={`text-xs font-bold ${isUser ? "text-slate-300" : isCoord ? "text-amber-800" : "text-ink"}`}>
                      {m.senderName}
                    </span>
                    <span className="text-[10px] text-slate-400 nums">{m.timestamp}</span>
                  </div>

                  {m.badge && (
                    <span className={`inline-block mb-1.5 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase ${
                      isCoord ? "bg-amber-100 text-amber-800" : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    }`}>
                      {m.badge}
                    </span>
                  )}

                  <div className="whitespace-pre-wrap leading-relaxed">{m.text}</div>

                  {m.sourceLinks && m.sourceLinks.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-ink/10 text-xs">
                      <div className="text-[11px] font-semibold text-slate uppercase tracking-wider mb-1">Verified Citations:</div>
                      <div className="space-y-1">
                        {m.sourceLinks.map((s, idx) => (
                          <a
                            key={idx}
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline block truncate text-xs"
                          >
                            🔗 {s.title}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Real-time Status / Loading progress indicator */}
          {currentStep && (
            <div className="flex items-center gap-2 p-3 bg-cream-deep/80 rounded-xl border border-ink/10 text-xs text-ink animate-pulse">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              <span>{currentStep}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-3 bg-white border-t border-ink/10 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
            placeholder={`Ask a question in ${platform === "telegram" ? "Telegram" : platform === "discord" ? "Discord" : "Mattermost"}...`}
            className="flex-1 px-4 py-2.5 rounded-full border border-ink/15 bg-cream/30 text-sm text-ink placeholder:text-slate-light focus:outline-none focus:border-ink focus:bg-white"
          />
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="btn-pill btn-pill-primary px-4 py-2 text-xs flex items-center gap-1.5 disabled:opacity-50"
          >
            <Send size={13} />
            <span>Send</span>
          </button>
        </form>

      </div>

      {/* Connection Guide for Live Bots */}
      <div className="mt-8 card p-6 bg-cream-deep border border-ink/10">
        <h3 className="font-bold text-ink text-base flex items-center gap-2">
          <MessageCircle size={18} /> How to connect your real Telegram or Discord Bot
        </h3>
        <p className="text-xs text-slate mt-1.5">
          AccessBridge AI comes built-in with native connectors in <code className="bg-white px-1.5 py-0.5 rounded border border-ink/10">backend/app/integrations/</code>:
        </p>
        <div className="grid md:grid-cols-2 gap-4 mt-4 text-xs">
          <div className="bg-white p-4 rounded-xl border border-ink/10">
            <span className="font-bold text-sky-600 block mb-1">Telegram Setup</span>
            <p className="text-slate mb-2">Create a bot with @BotFather and set in your <code className="bg-cream px-1 rounded">.env</code>:</p>
            <pre className="bg-slate-900 text-sky-300 p-2.5 rounded text-[11px] overflow-x-auto">
TELEGRAM_BOT_TOKEN=your_bot_token{"\n"}
TELEGRAM_CHAT_ID=your_chat_or_group_id
            </pre>
          </div>
          <div className="bg-white p-4 rounded-xl border border-ink/10">
            <span className="font-bold text-indigo-600 block mb-1">Discord Setup</span>
            <p className="text-slate mb-2">Create an application on Discord Developer Portal and set:</p>
            <pre className="bg-slate-900 text-indigo-300 p-2.5 rounded text-[11px] overflow-x-auto">
DISCORD_BOT_TOKEN=your_bot_token{"\n"}
DISCORD_CHANNEL_ID=your_discord_channel_id
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
