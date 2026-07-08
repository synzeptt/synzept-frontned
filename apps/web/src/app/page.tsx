import Link from "next/link";
import { ArrowRight, Bot, Brain, Sparkles, Workflow, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-background">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,hsl(187_92%_69%/0.12),transparent_50%)]" />
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles size={16} />
          </div>
          <span className="font-semibold">Synzept</span>
        </div>
        <nav className="flex items-center gap-2">
          <Link href="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/signup">
            <Button variant="primary">Get started</Button>
          </Link>
        </nav>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-6 pb-20 pt-16">
        <section className="mx-auto max-w-3xl text-center">
          <p className="mb-4 inline-flex rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium uppercase tracking-widest text-primary">
            AI-native workspace
          </p>
          <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
            The intelligent operating layer for modern teams
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Chat, memory, workflows, and semantic search — unified in a premium workspace connected to your Synzept backend.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/signup">
              <Button variant="primary" size="lg">
                Launch workspace
                <ArrowRight size={16} />
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg">
                Sign in
              </Button>
            </Link>
          </div>
        </section>

        <section className="mt-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: Bot, title: "Streaming chat", text: "Real-time AI responses with markdown and code highlighting." },
            { icon: Brain, title: "Memory", text: "Persistent context that grounds every conversation." },
            { icon: Workflow, title: "Workflows", text: "Visual automation for research and execution." },
            { icon: Zap, title: "Live updates", text: "Realtime activity stream from your workspace." }
          ].map(({ icon: Icon, title, text }) => (
            <article key={title} className="surface p-5">
              <div className="mb-3 grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                <Icon size={18} />
              </div>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{text}</p>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
