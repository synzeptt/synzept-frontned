"use client";

import { useEffect } from "react";

export function PwaInstaller() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch((error) => {
      console.warn("[Synzept PWA] Service worker registration failed", error);
    });
  }, []);

  return null;
}
