import { useEffect, useRef } from "react";

export default function UserIconBackground({ className = "" }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const group = document.getElementById("icon-dots-group");
    if (!group) return;

    // Clear previous if any
    group.innerHTML = "";

    const CX = 800; // horizontal center
    const NS = "http://www.w3.org/2000/svg";
    const CYAN = "#22d3ee";
    const WHITE = "#f0fbff";

    function dot(x: number, y: number, r: string, color: string, opacity: string) {
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", x.toFixed(2));
      c.setAttribute("cy", y.toFixed(2));
      c.setAttribute("r", r);
      c.setAttribute("fill", color);
      c.setAttribute("fill-opacity", opacity);
      if (group) group.appendChild(c);
    }

    function mirrored(x: number, y: number, r: string, color: string, opacity: string) {
      if (x === CX) {
        dot(x, y, r, color, opacity);
      } else {
        dot(x, y, r, color, opacity);
        dot(2 * CX - x, y, r, color, opacity);
      }
    }

    // Head
    const HEAD_CY = 360;
    const HEAD_R = 92;
    const STEP = 14;
    for (let gx = -HEAD_R; gx <= HEAD_R; gx += STEP) {
      for (let gy = -HEAD_R; gy <= HEAD_R; gy += STEP) {
        const d = Math.hypot(gx, gy);
        if (d > HEAD_R) continue;
        const t = d / HEAD_R;
        const color = t < 0.55 ? WHITE : CYAN;
        const opacity = (1 - t * 0.55).toFixed(2);
        const r = (5.2 - t * 1.6).toFixed(2);
        mirrored(CX + gx, HEAD_CY + gy, r, color, opacity);
      }
    }

    // Shoulders / body
    const BODY_CY = 640;
    const BODY_RX = 220;
    const BODY_RY = 190;
    const BSTEP = 16;
    for (let gx = -BODY_RX; gx <= BODY_RX; gx += BSTEP) {
      for (let gy = -BODY_RY; gy <= 0; gy += BSTEP) {
        const nx = gx / BODY_RX;
        const ny = gy / BODY_RY;
        const d = Math.hypot(nx, ny);
        if (d > 1) continue;
        const t = d;
        const color = t < 0.6 ? WHITE : CYAN;
        const opacity = (1 - t * 0.6).toFixed(2);
        const r = (4.6 - t * 1.4).toFixed(2);
        mirrored(CX + gx, BODY_CY + gy, r, color, opacity);
      }
    }

    // Soft outline ring
    const RING_N = 64;
    for (let i = 0; i < RING_N; i++) {
      const a = (i / RING_N) * Math.PI * 2;
      const x = CX + Math.cos(a) * (HEAD_R + 22);
      const y = HEAD_CY + Math.sin(a) * (HEAD_R + 22);
      if (Math.abs(x - CX) < 0.01) {
        dot(x, y, "2.2", WHITE, "0.9");
        continue;
      }
      mirrored(x, y, "2.2", WHITE, "0.9");
    }
  }, []);

  return (
    <div ref={containerRef} className={`relative overflow-hidden rounded-2xl ${className}`}>
      <svg
        viewBox="0 0 1600 900"
        preserveAspectRatio="xMidYMid slice"
        className="w-full h-full block"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="base" cx="50%" cy="46%" r="75%">
            <stop offset="0%" stopColor="#0d1d45" />
            <stop offset="45%" stopColor="#081431" />
            <stop offset="100%" stopColor="#02050f" />
          </radialGradient>

          <radialGradient id="vignette" cx="50%" cy="50%" r="70%">
            <stop offset="55%" stopColor="#000000" stopOpacity="0" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0.85" />
          </radialGradient>

          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur1" />
            <feGaussianBlur in="SourceGraphic" stdDeviation="22" result="blur2" />
            <feMerge>
              <feMergeNode in="blur2" />
              <feMergeNode in="blur1" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <radialGradient id="haze" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.18" />
            <stop offset="60%" stopColor="#0ea5e9" stopOpacity="0.05" />
            <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0" />
          </radialGradient>

          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <circle cx="20" cy="20" r="1.1" fill="#7dd3fc" fillOpacity="0.16" />
          </pattern>
        </defs>

        <rect width="1600" height="900" fill="url(#base)" />
        <rect width="1600" height="900" fill="url(#grid)" />
        <circle cx="800" cy="430" r="520" fill="url(#haze)" />

        <g id="icon-dots-group" filter="url(#glow)"></g>

        <rect width="1600" height="900" fill="url(#vignette)" />
      </svg>
    </div>
  );
}
