"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
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
        width: ref.current.offsetWidth || 360,
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
      <div
        role="button"
        tabIndex={CLIENT_ID && ready && !loading ? 0 : -1}
        aria-disabled={!CLIENT_ID || !ready || loading}
        className={cn(
          "relative flex h-11 w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-white px-4 text-sm font-medium text-stone-800 transition hover:bg-stone-50 hover:text-stone-950",
          (!CLIENT_ID || (!ready && !loading)) && "cursor-not-allowed opacity-80",
        )}
      >
        <span className="pointer-events-none flex items-center gap-3">
          {!ready && CLIENT_ID ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <GoogleIcon />
          )}
          Continue with Google
        </span>
        {CLIENT_ID && !ready && (
          <span className="pointer-events-none absolute right-4 text-xs font-normal text-muted">
            loading
          </span>
        )}
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 text-sm text-stone-700 backdrop-blur-sm">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Continuing...
          </div>
        )}
        {CLIENT_ID && (
          <div
            ref={ref}
            className={cn(
              "absolute inset-0 z-20 w-full opacity-0 [&>div]:h-11 [&>div]:w-full [&_iframe]:!m-0",
              !ready && "pointer-events-none",
            )}
            aria-hidden="true"
          />
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

function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.94H.96A9 9 0 0 0 0 9c0 1.45.35 2.82.96 4.06l3.01-2.34z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
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
