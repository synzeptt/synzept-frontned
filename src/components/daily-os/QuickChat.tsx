import { Input } from "@/components/ui/input";

export type QuickChatProps = {
  prompts: string[];
};

export function QuickChat({ prompts }: QuickChatProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Quick chat</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">Ask Synzept anything</h2>
      </div>
      <div className="mt-6 space-y-4">
        <Input placeholder="Ask Synzept anything..." aria-label="Quick chat question" />
        <div className="grid gap-3 sm:grid-cols-2">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-left text-sm text-stone-700 transition hover:bg-stone-100"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
