"use client";

import { useEffect, useRef } from "react";
import { useSettingsStore, type Appearance } from "@/stores/settings";

function getStoredAppearance(): Appearance | null {
  try {
    const appearance = localStorage.getItem("synzept-theme");
    return appearance === "dark" ? "dark" : appearance === "light" ? "light" : null;
  } catch {
    return null;
  }
}

function applyTheme(appearance: Appearance) {
  const root = document.documentElement;
  root.dataset.theme = appearance;
  root.style.colorScheme = appearance;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const appearance = useSettingsStore((state) => state.appearance);
  const setAppearance = useSettingsStore((state) => state.setAppearance);
  const initialized = useRef(false);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      const storedAppearance = getStoredAppearance();
      const resolvedAppearance = storedAppearance ?? appearance;
      applyTheme(resolvedAppearance);

      if (storedAppearance && storedAppearance !== appearance) {
        setAppearance(storedAppearance);
      }
      return;
    }

    applyTheme(appearance);
  }, [appearance, setAppearance]);

  return children;
}
