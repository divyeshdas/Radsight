import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background:  "var(--bg-primary)",
        surface:     "var(--bg-surface)",
        panel:       "var(--bg-panel)",
        elevated:    "var(--bg-elevated)",
        border:      "var(--border-color)",
        "border-subtle": "var(--border-subtle)",
        accent: {
          blue:    "var(--accent-blue)",
          cyan:    "var(--accent-cyan)",
          emerald: "var(--accent-emerald)",
          amber:   "var(--accent-amber)",
          rose:    "var(--accent-rose)",
          violet:  "var(--accent-violet)",
        },
        text: {
          primary:   "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted:     "var(--text-muted)",
          inverse:   "var(--text-inverse)",
        },
        severity: {
          normal:   "var(--severity-normal)",
          low:      "var(--severity-low)",
          moderate: "var(--severity-moderate)",
          high:     "var(--severity-high)",
          critical: "var(--severity-critical)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in":    "fadeIn 0.3s ease-in-out",
        "slide-up":   "slideUp 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
