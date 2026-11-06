import { useEffect, useState } from "react";
import { ShieldCheck, MessageSquare, Terminal, ExternalLink, Copy } from "lucide-react";
import { api } from "../services/api";

export default function Setup() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [switchHealth, setSwitchHealth] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.switchHealth().then(setSwitchHealth).catch(() => setSwitchHealth(null));
  }, []);

  return (
    <div className="max-w-editorial mx-auto px-6 py-10">
      <div className="notice text-slate uppercase tracking-wide">[Setup]</div>
      <h1 className="display text-3xl md:text-5xl text-ink mt-2">Connect Switch &amp; Mattermost</h1>
      <p className="text-slate mt-4 max-w-2xl leading-relaxed">
        AccessBridge integrates with Switch at two layers. Layer 1 (Switch Trust
        guardrails) wraps every LLM call in code and works without any desktop
        app. Layer 2 (Switch Console + Agent Bridge) routes room messages from
        Mattermost or Discord into the workflow.
      </p>

      {/* Live status */}
      <section className="grid md:grid-cols-2 gap-3 mt-8">
        <StatusCard
          title="Switch Trust guardrails"
          icon={<ShieldCheck size={16} />}
          ok={Boolean((health as any)?.switch_trust?.configured)}
          label={(health as any)?.switch_trust?.configured ? "Configured" : "Pass-through (set SWITCH_TRUST_API_KEY)"}
          detail={`SDK ${(health as any)?.switch_trust?.sdk_version ?? "—"} · gateway ${(health as any)?.switch_trust?.gateway_url ?? "—"}`}
        />
        <StatusCard
          title="Mattermost transport"
          icon={<MessageSquare size={16} />}
          ok={Boolean((health as any)?.mattermost?.configured)}
          label={(health as any)?.mattermost?.configured ? "Configured" : "Not configured"}
          detail={`bot_token=${(health as any)?.mattermost?.bot_token_configured ?? false} · webhook=${(health as any)?.mattermost?.incoming_webhook_configured ?? false}`}
        />
        <StatusCard
          title="Agent bridge endpoint"
          icon={<Terminal size={16} />}
          ok={Boolean(switchHealth?.bridge_enabled)}
          label={switchHealth?.bridge_enabled ? "Listening at /switch/bridge" : "Off"}
          detail={`POST /switch/bridge · POST /switch/mattermost/webhook`}
        />
        <StatusCard
          title="Bridge token"
          icon={<ShieldCheck size={16} />}
          ok={Boolean(switchHealth?.bridge_token_configured)}
          label={switchHealth?.bridge_token_configured ? "Configured" : "Open (set SWITCH_BRIDGE_TOKEN for production)"}
          detail="Verified on every inbound Switch / Mattermost event"
        />
      </section>

      {/* Layer 1 — Switch Trust */}
      <Section title="Layer 1 — Switch Trust guardrails (code-level)" subtitle="Always active. Wraps every LLM call from every agent.">
        <ol className="text-sm text-ink space-y-3 list-decimal pl-5">
          <li>
            Install the SDK:
            <CodeBlock>pip install switch-trust-sdk-py</CodeBlock>
          </li>
          <li>
            Set these environment variables (copy from <code className="notice bg-cream-deep px-1 rounded">.env.example</code>):
            <CodeBlock>{`SWITCH_TRUST_ENABLED=true
SWITCH_TRUST_GATEWAY_URL=https://api.switchagents.ai
SWITCH_TRUST_API_KEY=your-switch-trust-api-key
SWITCH_TRUST_POLICY_ID=optional-policy-id
# Optional, harden in production:
SWITCH_TRUST_REQUIRE_GUARDS=true`}</CodeBlock>
          </li>
          <li>
            Restart the backend. Every <code className="notice bg-cream-deep px-1 rounded">chat.completions.create</code> call
            from the Research, Language and Guidance agents is now routed through
            Switch Trust. Without a key, the SDK runs in pass-through mode and warns loudly.
          </li>
        </ol>
      </Section>

      {/* Layer 2 — Switch Console + Agent Bridge */}
      <Section title="Layer 2 — Switch Console + Agent Bridge" subtitle="Routes room messages from Mattermost/Discord into the workflow.">
        <ol className="text-sm text-ink space-y-3 list-decimal pl-5">
          <li>
            Install Switch Console for your platform from{" "}
            <a className="link-ink" href="https://github.com/sandbox-quantum/switch" target="_blank" rel="noreferrer noopener">
              sandbox-quantum/switch <ExternalLink size={11} className="inline" />
            </a>.
          </li>
          <li>Open Switch Console and talk to <code className="notice bg-cream-deep px-1 rounded">switch-buddy</code> to create your first agent and channel.</li>
          <li>Connect Mattermost (or Discord) as the chat platform inside Switch Console.</li>
          <li>
            Point the agent's bridge endpoint at AccessBridge:
            <CodeBlock>{`Bridge URL:   ${window.location.origin.replace(/:\d+$/, ':8000')}/switch/bridge
Method:       POST
Content-Type: application/json
Token header: <SWITCH_BRIDGE_TOKEN>   # required if SWITCH_BRIDGE_TOKEN is set`}</CodeBlock>
          </li>
          <li>
            Create the recommended rooms in Mattermost and join the agent to each:
            <CodeBlock>{`#student-questions   #research-updates   #translation   #human-review   #final-guidance`}</CodeBlock>
          </li>
        </ol>
      </Section>

      {/* Mattermost direct fallback */}
      <Section title="Mattermost direct (test without Switch Console)" subtitle="If you want to test end-to-end with Mattermost alone.">
        <ol className="text-sm text-ink space-y-3 list-decimal pl-5">
          <li>
            Set Mattermost env vars:
            <CodeBlock>{`MATTERMOST_ENABLED=true
MATTERMOST_BASE_URL=https://mattermost.your-org.com
MATTERMOST_BOT_TOKEN=your-bot-token
# OR a per-channel incoming webhook:
MATTERMOST_INCOMING_WEBHOOK_URL=https://mattermost.your-org.com/hooks/xxxx`}</CodeBlock>
          </li>
          <li>
            In Mattermost → Integrations → Outgoing Webhooks, create a webhook for
            <code className="notice bg-cream-deep px-1 rounded mx-1">#student-questions</code>
            pointed at:
            <CodeBlock>{`${window.location.origin.replace(/:\d+$/, ':8000')}/switch/mattermost/webhook`}</CodeBlock>
          </li>
          <li>Send a message in <code className="notice bg-cream-deep px-1 rounded">#student-questions</code>. AccessBridge will run the workflow and post progress + final guidance back.</li>
        </ol>
      </Section>

      <div className="hairline mt-10 pt-6 text-xs text-slate">
        Never commit <code className="notice bg-cream-deep px-1 rounded">.env</code> to git. The provided <code className="notice bg-cream-deep px-1 rounded">.gitignore</code> excludes it.
      </div>
    </div>
  );
}

function StatusCard({ title, icon, ok, label, detail }: { title: string; icon: React.ReactNode; ok: boolean; label: string; detail: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink font-medium">{icon} {title}</div>
        <span className={`status-pill ${ok ? "status-verified" : "status-partial"}`}>{ok ? "On" : "Off"}</span>
      </div>
      <div className="text-sm text-slate mt-2">{label}</div>
      <div className="text-xs text-slate-light mt-1 nums break-all">{detail}</div>
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      {subtitle && <p className="text-sm text-slate mt-0.5">{subtitle}</p>}
      <div className="card p-5 mt-3">{children}</div>
    </section>
  );
}

function CodeBlock({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <div className="mt-2 relative">
      <pre className="notice bg-cream-deep rounded-lg p-3 pr-10 text-xs text-ink overflow-x-auto whitespace-pre">{children}</pre>
      <button
        onClick={copy}
        className="absolute top-2 right-2 text-slate hover:text-ink"
        title="Copy"
      >
        {copied ? <span className="text-xs text-verified">copied</span> : <Copy size={13} />}
      </button>
    </div>
  );
}
