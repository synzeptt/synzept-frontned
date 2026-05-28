import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Brain, CheckCircle2, Layers3, LockKeyhole, NotebookTabs } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { SessionRedirect } from "@/components/auth/session-redirect";
import { SiteFooter } from "@/components/site-footer";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { buildStructuredData, createPageMetadata, SITE_DESCRIPTION } from "@/lib/seo";

export const metadata: Metadata = createPageMetadata({
  title: "Continuity-first AI workspace",
  description: SITE_DESCRIPTION,
  path: "/",
});

const values = [
  {
    title: "Memory that stays useful",
    text: "Durable context around goals, preferences, projects, and decisions, kept close enough to help without becoming noise.",
    icon: Brain,
  },
  {
    title: "Continuity across work",
    text: "Return to conversations, notes, tasks, and projects with a clearer sense of what was active and what needs attention.",
    icon: Layers3,
  },
  {
    title: "Organized by default",
    text: "A calm workspace for ongoing work, not another place where ideas disappear into disconnected fragments.",
    icon: NotebookTabs,
  },
  {
    title: "Built around trust",
    text: "Synzept focuses on dependable organization, transparent memory, and stable daily usefulness instead of feature noise.",
    icon: LockKeyhole,
  },
];

const workflow = [
  "Capture goals, projects, notes, and working context.",
  "Continue conversations without rebuilding the background every time.",
  "See active work, unfinished tasks, and continuity cues in one calm place.",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-surface text-stone-950">
      <SessionRedirect />
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="flex items-center gap-3" aria-label="Synzept home">
          <BrandLogo imageClassName="h-9" priority />
        </Link>
        <nav className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="#why" className="hidden px-3 py-2 transition hover:text-stone-950 sm:inline-block">
            Why it matters
          </Link>
          <Link href="/login" className="px-3 py-2 transition hover:text-stone-950">
            Login
          </Link>
          <Link href="/signup" className={buttonVariants({ size: "sm" })}>
            Try Synzept
          </Link>
        </nav>
      </header>

      <section className="border-y border-border bg-gradient-to-b from-white to-surface">
        <div className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-12 pt-10 sm:px-8 md:pt-16 lg:min-h-[calc(100vh-112px)] lg:grid-cols-[0.95fr_1.05fr] lg:pb-16">
          <div>
            <p className="mb-5 inline-flex rounded-full border border-border bg-white px-3 py-1 text-sm text-muted-foreground shadow-soft">
              AI workspace with memory
            </p>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[1.05] tracking-normal text-stone-950 sm:text-6xl">
              An AI workspace that remembers your projects, ideas, and conversations over time.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-stone-600">
              Synzept keeps memory, projects, notes, and AI conversations connected so every return feels like continuing,
              not starting over.
            </p>
            <div className="mt-6 grid gap-2 text-sm text-stone-700 sm:grid-cols-3">
              {["Continue yesterday's thread", "See recent focus", "Carry context forward"].map((item) => (
                <div key={item} className="rounded-md border border-border bg-white px-3 py-2 shadow-soft">
                  {item}
                </div>
              ))}
            </div>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "gap-2")}>
                Start with Synzept <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="#why" className={buttonVariants({ variant: "outline", size: "lg" })}>
                See how it works
              </Link>
            </div>
          </div>

          <div>
            <div className="rounded-xl border border-border bg-white p-5 shadow-panel">
              <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Today</p>
                  <p className="mt-1 text-lg font-semibold">Continuity workspace</p>
                </div>
                <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs text-emerald-700">
                  Context saved
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-5">
                <div className="space-y-3 sm:col-span-2">
                  {["Roadmap", "Onboarding", "Memory quality", "Daily review"].map((item) => (
                    <div key={item} className="rounded-lg border border-border bg-stone-50 p-3">
                      <p className="text-sm font-medium">{item}</p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">Ready to continue</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-border bg-stone-50 p-4 sm:col-span-3">
                  <p className="text-sm font-semibold">Resume thread</p>
                  <p className="mt-3 text-sm leading-6 text-stone-600">
                    You were exploring onboarding ideas yesterday. Continue the Synzept V1 refinement plan with trust,
                    memory relevance, and dashboard clarity in view.
                  </p>
                  <div className="mt-5 space-y-2">
                    {["Finish database readiness", "Retest signup flow", "Review memory retrieval"].map((item) => (
                      <div key={item} className="flex items-center gap-2 text-xs text-stone-600">
                        <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 rounded-lg border border-border bg-white p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-muted">Memory</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {[
                    "Prefers concise next steps",
                    "Build intentionally",
                    "Protect continuity",
                    "Observe real use",
                  ].map((item) => (
                    <div key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-600">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify({ "@context": "https://schema.org", "@graph": buildStructuredData() }) }}
      />

      <section id="why" className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Why Synzept</p>
          <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">Built for real daily continuity.</h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            Most tools capture fragments. Synzept is designed around what happens after the first note, chat, or task:
            returning tomorrow and knowing exactly where to continue.
          </p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {values.map((item) => (
            <article key={item.title} className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <item.icon className="h-5 w-5 text-accent" />
              <h3 className="mt-5 text-lg font-semibold">{item.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-border bg-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Daily usefulness</p>
            <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">A calmer way to keep momentum.</h2>
          </div>
          <div className="space-y-4">
            {workflow.map((item, index) => (
              <div key={item} className="flex gap-4 rounded-lg border border-border bg-surface p-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-900 text-sm font-semibold text-white">
                  {index + 1}
                </span>
                <p className="text-sm leading-6 text-stone-700">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="rounded-xl border border-border bg-white p-6 shadow-panel sm:p-8 lg:flex lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Ready to continue with more clarity?</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              Start with your current priorities. Synzept helps turn ongoing context into a workspace you can return to.
            </p>
          </div>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row lg:mt-0">
            <Link href="/signup" className={buttonVariants()}>
              Try Synzept
            </Link>
            <Link href="/login" className={buttonVariants({ variant: "ghost" })}>
              Login
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
