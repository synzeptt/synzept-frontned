import Link from "next/link";
import type { ReactNode } from "react";
import { AlertCircle, BookOpen, CheckCircle2, LifeBuoy, Shield } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { PageHeader } from "@/components/layout/page-header";

const faqs = [
  {
    q: "What should I do first after setup?",
    a: "Open the dashboard and start with Continue Working. If it is empty, create one project, task, note, or thread so Synzept has a restore point.",
  },
  {
    q: "What does Synzept remember?",
    a: "Synzept stores useful context such as goals, priorities, work preferences, project facts, and decisions. It is designed to remember meaning, not every word.",
  },
  {
    q: "How do I fix a wrong memory?",
    a: "Open Settings, review Memory control, edit the memory text, or delete it. You can also flag memory behavior from feedback.",
  },
  {
    q: "What should I do if a response fails?",
    a: "Use Retry in chat. Synzept stores the conversation state and logs the failure safely so the response can be recovered.",
  },
  {
    q: "How should I use projects?",
    a: "Create one project per meaningful area of work. Notes, tasks, conversations, and memories can then share a continuity layer.",
  },
  {
    q: "How do I continue work naturally?",
    a: "Use continuation cards, open a recent thread, or ask Synzept to resume a project. The system works best when unfinished context has a project, task, note, or conversation attached.",
  },
];

const recovery = [
  "If chat stalls, stop the stream and retry.",
  "If the dashboard looks sparse, add one project, one task, or one note.",
  "If Synzept misses context, add a note or memory from Settings.",
  "If a save fails, stay on the page. Forms keep your current text so you can retry.",
  "If personalization feels too strong, pause Memory or Personalization in Settings.",
];

export default function HelpPage() {
  return (
    <div className="h-[100dvh] overflow-y-auto">
      <PageHeader label="Support" title="Help" />
      <main className="mx-auto max-w-5xl space-y-6 px-5 py-6 md:px-8">
        <section className="rounded-md border border-border bg-white p-5">
          <div className="flex items-start gap-4">
            <div>
              <BrandLogo imageClassName="h-9" />
              <h2 className="mt-4 text-lg font-semibold text-stone-950">Using Synzept well</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
                Synzept works best when you give it a small amount of durable context: what matters,
                what you are trying to move forward, and where work should continue tomorrow.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <HelpCard
            icon={<BookOpen className="h-4 w-4" />}
            title="Onboarding"
            text="Add goals, priorities, and one starter project. You can change everything later."
          />
          <HelpCard
            icon={<Shield className="h-4 w-4" />}
            title="Memory control"
            text="View, edit, delete, pause learning, or disable personalization from Settings."
          />
          <HelpCard
            icon={<LifeBuoy className="h-4 w-4" />}
            title="Feedback"
            text="Use the feedback button for bugs, memory issues, response quality, or UX friction."
          />
        </section>

        <section className="rounded-md border border-border bg-white p-5">
          <h2 className="text-sm font-medium text-stone-950">First-use path</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            {[
              "Add one project for ongoing work.",
              "Capture one next action.",
              "Start one thread with what feels unfinished.",
              "Return to Continue Working tomorrow.",
            ].map((item) => (
              <p key={item} className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-stone-600">
                {item}
              </p>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-md border border-border bg-white p-5">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-medium text-stone-950">
              <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
              FAQ
            </h2>
            <div className="space-y-4">
              {faqs.map((item) => (
                <div key={item.q} className="border-b border-border pb-4 last:border-0 last:pb-0">
                  <p className="text-sm font-medium text-stone-900">{item.q}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.a}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-border bg-white p-5">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-medium text-stone-950">
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
              Recovery Guide
            </h2>
            <div className="space-y-2">
              {recovery.map((item) => (
                <p key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-600">
                  {item}
                </p>
              ))}
            </div>
            <Link href="/settings" className="mt-4 inline-block text-sm text-accent hover:underline">
              Open Settings
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

function HelpCard({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-md border border-border bg-white p-4">
      <div className="mb-3 text-muted-foreground">{icon}</div>
      <p className="text-sm font-medium text-stone-950">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
    </div>
  );
}
