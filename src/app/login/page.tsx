"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { BrandLogo } from "@/components/brand-logo";
import { CopyrightLine } from "@/components/copyright-line";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GoogleSignIn } from "@/components/auth/google-sign-in";
import { useAuthStore } from "@/stores/auth";

export function AuthEntry({ initialMode = "login" }: { initialMode?: "login" | "signup" }) {
  const router = useRouter();
  const { login, signup } = useAuthStore();
  const [mode, setMode] = useState<"login" | "signup">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const path =
        mode === "login"
          ? await login(email, password)
          : await signup(email, password);
      router.replace(path);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (mode === "login" && /invalid email|password|credentials|unauthorized|sign in/i.test(message)) {
        setError("Invalid email or password.");
      } else {
        setError(message || "Authentication failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-10 text-stone-950">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md rounded-xl border border-border bg-white p-8 shadow-panel"
      >
        <div className="mb-8">
          <BrandLogo imageClassName="h-11" priority />
          <p className="mt-3 text-sm text-muted">A calm workspace for continuity</p>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs text-muted">Email</label>
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs text-muted">Password</label>
            <Input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
            />
            {mode === "login" && (
              <div className="mt-2 text-right">
                <Link href="/forgot-password" className="text-xs text-muted hover:text-stone-950">
                  Forgot password?
                </Link>
              </div>
            )}
          </div>
          {error && (
            <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <div className="mt-6">
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-[0.14em]">
              <span className="bg-white px-3 text-muted">or</span>
            </div>
          </div>
          <GoogleSignIn mode={mode === "signup" ? "signup" : "signin"} />
        </div>

        <p className="mt-6 text-center text-sm text-muted">
          {mode === "login" ? "New to Synzept?" : "Already have an account?"}{" "}
          <Link
            href={mode === "login" ? "/signup" : "/login"}
            className="text-accent hover:underline"
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
          >
            {mode === "login" ? "Create account" : "Sign in"}
          </Link>
        </p>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-muted">
          Synzept uses the context you choose to share to preserve continuity.
          You can edit or delete memories anytime.
        </p>
        <p className="mt-4 text-center text-xs text-muted">
          <Link href="/" className="hover:text-stone-950">
            Back to overview
          </Link>
        </p>
        <CopyrightLine className="mt-5 text-center" />
      </motion.div>
    </div>
  );
}

export default function LoginPage() {
  return <AuthEntry initialMode="login" />;
}
