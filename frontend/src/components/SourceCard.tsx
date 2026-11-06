import { FileText, ExternalLink, Check, AlertCircle } from "lucide-react";
import type { SourceOut } from "../types";

export default function SourceCard({ source }: { source: SourceOut }) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-slate">
            <FileText size={13} />
            <span className="truncate">{source.publisher || "Official source"}</span>
          </div>
          <div className="mt-1.5 text-ink font-medium leading-snug">
            {source.title || source.url}
          </div>
        </div>
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer noopener"
          className="text-slate hover:text-ink shrink-0"
          title="Open official source"
        >
          <ExternalLink size={16} />
        </a>
      </div>
      {source.snippet && (
        <p className="text-sm text-slate mt-3 leading-relaxed line-clamp-3">
          {source.snippet}
        </p>
      )}
      <div className="hairline mt-3 pt-2.5 flex items-center justify-between text-xs">
        <span className={`inline-flex items-center gap-1 ${source.reachable ? "text-verified" : "text-amber"}`}>
          {source.reachable ? <Check size={12} /> : <AlertCircle size={12} />}
          {source.reachable ? "Fetched live" : "Bundled excerpt (offline)"}
        </span>
        <span className="text-slate nums">
          Retrieved {new Date(source.retrieved_at).toLocaleString()}
        </span>
      </div>
    </div>
  );
}
