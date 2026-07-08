import { ArrowRight, BarChart3, Sparkles, TrendingUp } from "lucide-react";

const stats = [
  { label: "Product health", value: "78/100", hint: "Healthy with onboarding friction" },
  { label: "Activation", value: "63%", hint: "Onboarding completion" },
  { label: "Retention", value: "41%", hint: "Current cohort" },
];

const insights = [
  {
    title: "Daily Brief drives activation",
    detail: "Users who reach the brief complete onboarding more often and return sooner.",
  },
  {
    title: "Workspace setup is the main drop-off",
    detail: "The setup phase is where the largest friction spike appears in the funnel.",
  },
];

const recommendations = [
  { title: "Surface Daily Brief earlier", impact: "High" },
  { title: "Simplify workspace setup", impact: "High" },
  { title: "Improve search discoverability", impact: "Medium" },
];

export default function EvolutionPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Founder dashboard</p>
              <h1 className="text-3xl font-semibold">Synzept Evolution Engine</h1>
            </div>
          </div>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-stone-600">
            This internal dashboard summarizes product health, activation, retention trends, and the recommendations most likely to improve the experience.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          {stats.map((item) => (
            <div key={item.label} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
              <p className="text-sm text-stone-500">{item.label}</p>
              <p className="mt-3 text-3xl font-semibold">{item.value}</p>
              <p className="mt-2 text-sm text-stone-600">{item.hint}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-stone-700" />
              <h2 className="text-xl font-semibold">Recent insights</h2>
            </div>
            <div className="mt-5 space-y-4">
              {insights.map((item) => (
                <div key={item.title} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <p className="font-medium">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-stone-600">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-stone-700" />
              <h2 className="text-xl font-semibold">Top recommendations</h2>
            </div>
            <div className="mt-5 space-y-3">
              {recommendations.map((item) => (
                <div key={item.title} className="flex items-center justify-between rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="text-sm text-stone-600">Estimated impact: {item.impact}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-stone-500" />
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
