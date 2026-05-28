"use client";

import { useEffect, useState } from "react";
import { Theme, applyTheme, getStoredTheme, toggleTheme } from "@/lib/theme";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = getStoredTheme();
    setTheme(stored);
    applyTheme(stored);
  }, []);

  const toggle = () => {
    const next = toggleTheme(theme);
    setTheme(next);
    applyTheme(next);
  };

  return { theme, toggle, isDark: theme === "dark" };
}
