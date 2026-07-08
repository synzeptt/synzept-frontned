import { Button } from "@/components/ui/button";

export type SuggestionCard = {
  id: string;
  title: string;
  description: string;
};

export type SuggestionsProps = {
  suggestions: SuggestionCard[];
  onAct: (suggestionId: string) => void;
};

export function Suggestions({ suggestions, onAct }: SuggestionsProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Suggestions</p>
          <h2 className="mt-3 text-2xl font-semibold text-stone-950">What to consider next</h2>
        </div>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {suggestions.map((suggestion) => (
          <div key={suggestion.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <h3 className="text-base font-semibold text-stone-950">{suggestion.title}</h3>
            <p className="mt-2 text-sm leading-6 text-stone-600">{suggestion.description}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-5"
              onClick={() => onAct(suggestion.id)}
            >
              Review
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}
