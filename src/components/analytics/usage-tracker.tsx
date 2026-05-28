"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { api, getAccessToken } from "@/lib/api";

export function UsageTracker() {
  const pathname = usePathname();

  useEffect(() => {
    const analyticsEnabled = localStorage.getItem("synzept-analytics-enabled");
    if (analyticsEnabled === "false") return;
    if (!getAccessToken()) return;
    const started = performance.now();
    api.trackEvent("daily_active", "app", { pathname });
    api.trackEvent("page_view", pathname.replace("/", "") || "dashboard", { pathname });
    if (!sessionStorage.getItem("synzept-return-session-tracked")) {
      sessionStorage.setItem("synzept-return-session-tracked", "1");
      api.trackEvent("return_session", "app", {
        pathname,
        referrer: document.referrer || null,
      });
    }
    const frame = requestAnimationFrame(() => {
      api.trackEvent("frontend_render", "app", {
        pathname,
        render_ms: Math.round(performance.now() - started),
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [pathname]);

  return null;
}
