"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export default function EarlyAccessPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [intendedUse, setIntendedUse] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setStatus("loading");
    try {
      await api.joinWaitlist({
        email,
        name: name || undefined,
        role: role || undefined,
        intended_use: intendedUse || undefined,
      });
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join the waitlist");
      setStatus("idle");
    }
  };

  return (
    <main className="min-h-screen bg-surface px-4 py-8 text-stone-950">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col justify-between">
        <nav className="flex items-center justify-between">
          <BrandLogo imageClassName="h-9" />
          <Link href="/login" className="text-sm text-muted hover:text-stone-950">
            Sign in
          </Link>
        </nav>

        <section className="grid gap-10 py-12 md:grid-cols-[1.05fr_0.95fr] md:items-center">
          <div>
            <p className="mb-3 text-xs font-medium uppercase tracking-widest text-accent">Early access</p>
            <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-stone-950 md:text-6xl">
              Synzept is a continuity-first AI workspace for life and work.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-muted">
              V1 is opening carefully for people who want continuity, useful organization, and a dependable place to return to ongoing work.
            </p>
            <div className="mt-8 grid gap-3 text-sm text-stone-700 sm:grid-cols-2">
              {["Memory continuity", "Project follow-through", "Daily usefulness", "User-controlled context"].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-accent" />
                  {item}
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={submit} className="rounded-2xl border border-border bg-surface-raised p-5 shadow-panel">
            {status === "done" ? (
              <div className="py-8 text-center">
                <CheckCircle2 className="mx-auto h-10 w-10 text-accent" />
                <h2 className="mt-4 text-lg font-semibold">You are on the waitlist</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Thanks. Early access is being opened in controlled groups so the product can stay stable and useful.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs text-muted">Email</label>
                  <Input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-muted">Name</label>
                  <Input value={name} onChange={(event) => setName(event.target.value)} />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-muted">Role or work type</label>
                  <Input value={role} onChange={(event) => setRole(event.target.value)} />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs text-muted">What would make Synzept useful daily?</label>
                  <Textarea value={intendedUse} onChange={(event) => setIntendedUse(event.target.value)} className="min-h-28" />
                </div>
                {error && <p className="text-sm text-red-400">{error}</p>}
                <Button type="submit" className="w-full" disabled={status === "loading"}>
                  {status === "loading" ? "Joining..." : "Join waitlist"}
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </div>
            )}
          </form>
        </section>
      </div>
    </main>
  );
}
