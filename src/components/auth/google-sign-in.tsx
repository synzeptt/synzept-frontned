"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (parent: HTMLElement, config: Record<string, unknown>) => void;
          cancel?: () => void;
        };
      };
    };
  }
}

export function GoogleSignIn({ mode = "signin" }: { mode?: "signin" | "signup" }) {
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { googleLogin } = useAuthStore();
  const [error, setError] = useState<string | null>(
    CLIENT_ID ? null : "Google sign-in needs NEXT_PUBLIC_GOOGLE_CLIENT_ID before it can open.",
  );
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!CLIENT_ID) {
      console.warn("Synzept Google sign-in is visible but NEXT_PUBLIC_GOOGLE_CLIENT_ID is not configured.");
      return;
    }
    if (!ref.current) return;
    let cancelled = false;

    const init = () => {
      if (cancelled || !window.google?.accounts?.id || !ref.current) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        ux_mode: "popup",
        callback: async (response: { credential?: string }) => {
          if (!response.credential) {
            setError("Google did not return a sign-in token. Please try again.");
            return;
          }
          setError(null);
          setLoading(true);
          try {
            const path = await googleLogin(response.credential);
            router.replace(path);
          } catch (err) {
            setError(cleanGoogleError(err));
          } finally {
            setLoading(false);
          }
        },
      });
      ref.current.innerHTML = "";
      window.google.accounts.id.renderButton(ref.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        width: Math.max(ref.current.offsetWidth || 0, 320),
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
      });
      setReady(true);
    };

    if (window.google?.accounts?.id) {
      init();
      return () => {
        cancelled = true;
      };
    }

    const existing = document.querySelector<HTMLScriptElement>("script[data-synzept-google-auth='true']");
    const script = existing || document.createElement("script");
    if (!existing) {
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.dataset.synzeptGoogleAuth = "true";
      script.onerror = () => {
        setReady(false);
        setError("Google sign-in is unavailable right now. You can continue with email.");
      };
      document.body.appendChild(script);
    }
    script.addEventListener("load", init);
    return () => {
      cancelled = true;
      script.removeEventListener("load", init);
      window.google?.accounts?.id.cancel?.();
    };
  }, [googleLogin, router]);

  return (
    <div className="space-y-2">
      <div className="relative min-h-11 w-full overflow-hidden rounded-lg">
        {!ready && (
          <button
            type="button"
            disabled
            className="flex h-11 w-full cursor-not-allowed items-center justify-center rounded-lg border border-border bg-white px-4 text-sm font-medium text-stone-700 opacity-80"
          >
            {CLIENT_ID ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Continue with Google
          </button>
        )}
        {CLIENT_ID && (
          <div
            ref={ref}
            className={`min-h-11 w-full [&>div]:mx-auto [&>div]:!w-full [&_iframe]:!m-0 ${
              ready ? "" : "pointer-events-none absolute inset-0 opacity-0"
            }`}
          />
        )}
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-white/80 text-sm text-stone-700 backdrop-blur-sm">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Continuing...
          </div>
        )}
      </div>
      {error && (
        <p className="rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-center text-sm text-amber-800" role="status">
          {error}
        </p>
      )}
      <p className="text-center text-[11px] leading-relaxed text-muted">
        {mode === "signup" ? "New Google users still set up their continuity workspace." : "Use the same Google account to return to your workspace."}
      </p>
    </div>
  );
}

function cleanGoogleError(err: unknown) {
  const message = err instanceof Error ? err.message : "";
  if (/invalid google token|google email|google account/i.test(message)) {
    return "Google could not verify this account. Please try again or continue with email.";
  }
  if (/network|reach the backend|fetch/i.test(message)) {
    return "Synzept could not reach the server. Please check your connection and try again.";
  }
  return message || "Google sign-in failed. Please try again.";
}
