// Visual motifs inspired by the AgenticX editorial aesthetic, adapted to
// AccessBridge's navy/cream palette. These are pure CSS/SVG — no fake photos.

export function DitherPortrait({ className = "" }: { className?: string }) {
  // A dot-matrix / halftone-style abstract portrait silhouette built from
  // CSS radial-gradient dots. Purely decorative — no fake person photo.
  return (
    <div
      className={`dither-bg relative overflow-hidden rounded-2xl bg-ink ${className}`}
      aria-hidden
    >
      <div className="absolute inset-0 opacity-90"
        style={{
          backgroundImage:
            "radial-gradient(rgba(220,235,250,0.22) 1px, transparent 1px)",
          backgroundSize: "5px 5px",
        }}
      />
      <div className="absolute inset-0 flex items-end justify-center">
        <svg viewBox="0 0 200 220" className="h-full w-full">
          <defs>
            <radialGradient id="halo" cx="50%" cy="40%" r="60%">
              <stop offset="0%" stopColor="#DCEBFA" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#14263D" stopOpacity="0" />
            </radialGradient>
            <pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse">
              <circle cx="3" cy="3" r="1.4" fill="#DCEBFA" opacity="0.55" />
            </pattern>
          </defs>
          <rect width="200" height="220" fill="url(#halo)" />
          {/* abstract shoulders + head silhouette filled with the dot pattern */}
          <path
            d="M100 40 C 120 40, 132 56, 132 78 C 132 100, 120 116, 100 116 C 80 116, 68 100, 68 78 C 68 56, 80 40, 100 40 Z M40 220 C 40 170, 70 140, 100 140 C 130 140, 160 170, 160 220 Z"
            fill="url(#dots)"
          />
        </svg>
      </div>
    </div>
  );
}

export function BarField({ seed = 42, count = 64, className = "" }: { seed?: number; count?: number; className?: string }) {
  // ASCII-waveform / barcode-bloom accent — vertical bars of varying heights.
  const heights = Array.from({ length: count }, (_, i) => {
    const v = Math.sin((i + seed) * 0.21) * 0.5 + Math.cos((i + seed) * 0.07) * 0.5;
    return 20 + Math.abs(v) * 80; // 20–100 px
  });
  return (
    <div className={`bar-field ${className}`} aria-hidden>
      {heights.map((h, i) => (
        <span key={i} style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}

export function Notice({ label, children }: { label: string; children: React.ReactNode }) {
  // Monospace agent "notice" toast — mirrors the AgenticX terminal motif.
  return (
    <div className="card p-3.5 flex items-start gap-3">
      <span className="mt-0.5 inline-block h-1.5 w-1.5 rounded-full bg-ink" />
      <div className="min-w-0">
        <div className="notice text-slate uppercase tracking-wide">[{label}]</div>
        <div className="text-sm text-ink mt-0.5 leading-snug">{children}</div>
      </div>
    </div>
  );
}
