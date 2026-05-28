"use client";

import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { isDark, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className="relative flex h-8 w-14 items-center rounded-full border transition-colors duration-200"
      style={{
        backgroundColor: isDark ? "var(--bg-elevated)" : "var(--border-subtle)",
        borderColor: "var(--border-color)",
      }}
    >
      <span
        className="absolute flex h-6 w-6 items-center justify-center rounded-full text-xs transition-all duration-200"
        style={{
          left: isDark ? "calc(100% - 28px)" : "2px",
          backgroundColor: isDark ? "var(--accent-blue)" : "var(--accent-amber)",
        }}
      >
        {isDark ? "🌙" : "☀️"}
      </span>
    </button>
  );
}
