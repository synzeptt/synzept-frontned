"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BrandLogo } from "@/components/brand-logo";
import { CopyrightLine } from "@/components/copyright-line";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(token ? null : "This reset link is missing its secure token.");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (password.length < 8) {
      setError("Use at least 8 characters for your new password.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The passwords do not match yet.");
      return;
    }
    setLoading(true);
    try {
      const response = await api.resetPassword(token, password);
      setMessage(response.message);
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "We could not reset your password. Please request a new link.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="mb-1.5 block text-xs text-muted">New password</label>
        <Input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="New password"
          disabled={!token || Boolean(message)}
        />
      </div>
      <div>
        <label className="mb-1.5 block text-xs text-muted">Confirm password</label>
        <Input
          type="password"
          required
          minLength={8}
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          placeholder="Confirm password"
          disabled={!token || Boolean(message)}
        />
      </div>

      {message && (
        <p className="rounded-md border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-800" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={loading || !token || Boolean(message)}>
        {loading ? "Updating..." : "Update password"}
      </Button>
      {message && (
        <Link
          href="/login"
          className="inline-flex h-10 w-full items-center justify-center rounded-lg border border-border bg-white px-5 text-sm font-medium text-stone-700 transition hover:bg-stone-50 hover:text-stone-950"
        >
          Return to sign in
        </Link>
      )}
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-10 text-stone-950">
      <div className="w-full max-w-md rounded-xl border border-border bg-white p-8 shadow-panel">
        <div className="mb-8">
          <BrandLogo imageClassName="h-11" priority />
          <p className="mt-3 text-sm text-muted">Choose a new password for your Synzept account.</p>
        </div>
        <Suspense fallback={<p className="text-sm text-muted">Opening your reset link...</p>}>
          <ResetPasswordForm />
        </Suspense>
        <CopyrightLine className="mt-6 text-center" />
      </div>
    </div>
  );
}
