import { Button } from "@/components/ui/button";

export type WelcomeScreenProps = {
  onBegin: () => void;
};

export function WelcomeScreen({ onBegin }: WelcomeScreenProps) {
  return (
    <section className="rounded-[32px] border border-stone-200 bg-white px-6 py-8 shadow-soft sm:px-8 sm:py-10">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Welcome to Synzept</p>
        <h1 className="mt-5 text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">Instead of organizing your work...</h1>
        <p className="mt-4 text-base leading-7 text-stone-600">Let's first understand you.</p>
      </div>
      <div className="mt-8 sm:mt-10">
        <Button onClick={onBegin} className="w-full py-4 text-base font-semibold">
          Begin
        </Button>
      </div>
    </section>
  );
}
