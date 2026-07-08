import { Button } from "@/components/ui/button";

export type CompletionScreenProps = {
  onEnter: () => void;
};

export function CompletionScreen({ onEnter }: CompletionScreenProps) {
  return (
    <section className="rounded-[32px] border border-stone-200 bg-white px-6 py-8 shadow-soft sm:px-8 sm:py-10">
      <div className="space-y-6 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">You're all set</p>
        <h1 className="text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">Synzept will now begin learning from every conversation, project, and decision you make.</h1>
        <p className="mx-auto max-w-2xl text-base leading-7 text-stone-600">The workspace will adapt to your role, goals, preferences, and current work so everything feels personalized from day one.</p>
        <Button onClick={onEnter} className="w-full py-4 text-base font-semibold">
          Enter Workspace
        </Button>
      </div>
    </section>
  );
}
