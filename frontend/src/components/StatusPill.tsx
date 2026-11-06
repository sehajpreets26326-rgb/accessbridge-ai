import { CheckCircle2, AlertTriangle, CircleDashed, XCircle, Clock, Loader2 } from "lucide-react";

const labelMap: Record<string, string> = {
  received: "Received",
  researching: "Researching",
  translating: "Translating",
  guiding: "Guiding",
  awaiting_review: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
  delivered: "Delivered",
  failed: "Failed",
  verified: "Verified",
  partial: "Partial",
  unverified: "Unverified",
  started: "Started",
  success: "Success",
  error: "Error",
  skipped: "Skipped",
};

export default function StatusPill({ status }: { status: string }) {
  const cls = `status-pill status-${status}`;
  const Icon = iconFor(status);
  return (
    <span className={cls}>
      <Icon size={11} />
      {labelMap[status] ?? status}
    </span>
  );
}

function iconFor(status: string) {
  if (["approved", "delivered", "verified", "success"].includes(status)) return CheckCircle2;
  if (["rejected", "failed", "error", "unverified"].includes(status)) return XCircle;
  if (["awaiting_review", "partial", "started", "uncertain"].includes(status)) return AlertTriangle;
  if (["received", "researching", "translating", "guiding"].includes(status)) return Loader2;
  if (["missing", "todo"].includes(status)) return CircleDashed;
  return Clock;
}
