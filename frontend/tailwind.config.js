/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14263D",
        "ink-soft": "#1E3A5F",
        cream: "#F7F7F2",
        "cream-deep": "#EFECE4",
        softblue: "#DCEBFA",
        slate: "#667085",
        "slate-light": "#98A2B3",
        verified: "#15803D",
        "verified-soft": "#DCFCE7",
        amber: "#B45309",
        "amber-soft": "#FEF3C7",
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.04em',
      },
      maxWidth: {
        editorial: '68rem',
      },
      boxShadow: {
        card: '0 1px 0 0 rgba(20, 38, 61, 0.06), 0 1px 2px 0 rgba(20, 38, 61, 0.04)',
        lift: '0 4px 12px -2px rgba(20, 38, 61, 0.08), 0 2px 4px -1px rgba(20, 38, 61, 0.04)',
      },
    },
  },
  plugins: [],
};
