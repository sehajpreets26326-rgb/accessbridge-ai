import { NavLink, Outlet } from "react-router-dom";
import { BookOpen, LayoutDashboard, Send, Cpu, ClipboardCheck, MessageSquare, Settings } from "lucide-react";

const navItems = [
  { to: "/", label: "Home", icon: BookOpen, end: true },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/chat-demo", label: "Chat Simulation", icon: MessageSquare },
  { to: "/ask", label: "Ask", icon: Send },
  { to: "/agents", label: "Agents", icon: Cpu },
  { to: "/review", label: "Review", icon: ClipboardCheck },
  { to: "/setup", label: "Setup", icon: Settings },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-[#FBFBFA]">
      <SiteNav />
      <main className="flex-1">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}

function SiteNav() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur bg-cream/90 border-b border-ink/10 shadow-xs">
      <div className="max-w-editorial mx-auto px-6 h-14 flex items-center justify-between">
        <NavLink to="/" className="flex items-center gap-2 text-ink">
          <Mark />
          <span className="font-semibold tracking-tight">AccessBridge</span>
          <span className="text-slate text-xs hidden sm:inline">AI</span>
        </NavLink>
        <nav className="hidden md:flex items-center gap-1">
          {navItems.slice(1).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  isActive ? "text-ink bg-softblue/80 shadow-xs" : "text-slate hover:text-ink"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <NavLink to="/chat-demo" className="btn-pill btn-pill-ghost text-xs border border-ink/15 hidden sm:flex items-center gap-1">
            <MessageSquare size={13} /> Chat Demo
          </NavLink>
          <NavLink to="/ask" className="btn-pill btn-pill-primary text-sm flex items-center gap-1.5">
            <Send size={13} /> Ask
          </NavLink>
        </div>
      </div>
      {/* Mobile nav strip */}
      <div className="md:hidden border-t border-ink/10 overflow-x-auto bg-white/70">
        <div className="flex items-center gap-1 px-3 py-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `px-3 py-1 rounded-full text-xs whitespace-nowrap font-medium ${
                  isActive ? "text-ink bg-softblue" : "text-slate"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="hairline mt-24 bg-white/60">
      <div className="max-w-editorial mx-auto px-6 py-10 grid md:grid-cols-3 gap-8 text-sm">
        <div>
          <div className="flex items-center gap-2 text-ink">
            <Mark />
            <span className="font-semibold">AccessBridge AI</span>
          </div>
          <p className="text-slate mt-3 max-w-xs leading-relaxed text-xs">
            Making essential information understandable and accessible to everyone.
            Multi-agent, source-backed guidance for scholarships and educational opportunities.
          </p>
        </div>
        <div>
          <div className="text-ink font-medium mb-3 text-xs uppercase tracking-wider">Multi-Platform Chat Transports</div>
          <ul className="text-slate space-y-1.5 text-xs">
            <li>Telegram Bot API (@AccessBridgeAIBot)</li>
            <li>Discord REST Gateway / Slash commands</li>
            <li>Mattermost &amp; Switch Console Bridge</li>
          </ul>
        </div>
        <div>
          <div className="text-ink font-medium mb-3 text-xs uppercase tracking-wider">Trust Contract</div>
          <ul className="text-slate space-y-1.5 text-xs">
            <li>Official-source preference (100% cited)</li>
            <li>Retrieval timestamps on every source</li>
            <li>Human Coordinator review gate</li>
            <li>Zero hallucinations policy</li>
          </ul>
        </div>
      </div>
      <div className="hairline">
        <div className="max-w-editorial mx-auto px-6 py-4 text-xs text-slate flex items-center justify-between">
          <span>© {new Date().getFullYear()} AccessBridge AI — Live Multi-Agent System</span>
          <span className="notice text-verified font-medium">● Switch Trust &amp; Backend Connected</span>
        </div>
      </div>
    </footer>
  );
}

function Mark() {
  return (
    <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="6" fill="#14263D" />
      <path d="M8 20 L16 8 L24 20 M11 20 L16 13 L21 20" stroke="#DCEBFA" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="24" r="1.6" fill="#F7F7F2" />
    </svg>
  );
}
