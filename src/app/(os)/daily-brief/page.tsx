import { DailyGreeting } from "@/components/daily-os/DailyGreeting";
import { HighestPriority } from "@/components/daily-os/HighestPriority";
import { Insights } from "@/components/daily-os/Insights";
import { OpenLoops } from "@/components/daily-os/OpenLoops";
import { ProgressOverview } from "@/components/daily-os/ProgressOverview";
import { QuickChat } from "@/components/daily-os/QuickChat";
import { Recommendations } from "@/components/daily-os/Recommendations";
import { RecentChanges } from "@/components/daily-os/RecentChanges";
import { DailyLayout } from "@/components/daily-os/DailyLayout";
import { dailyOSMock } from "@/data/dailyOSMock";

export default function DailyBriefPage() {
  const {
    userName,
    highestPriority,
    sinceLastVisit,
    openLoops,
    progress,
    insights,
    recommendations,
    quickChatPrompts,
  } = dailyOSMock;

  return (
    <main className="min-h-screen bg-surface py-8 text-stone-950">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <DailyLayout>
          <DailyGreeting name={userName} />

          <div className="grid gap-6 xl:grid-cols-[0.95fr_0.65fr]">
            <div className="space-y-6">
              <HighestPriority
                title={highestPriority.title}
                reason={highestPriority.reason}
                impact={highestPriority.impact}
                actionLabel={highestPriority.actionLabel}
              />
              <RecentChanges items={sinceLastVisit} />
            </div>

            <div className="space-y-6">
              <ProgressOverview items={progress} />
              <OpenLoops loops={openLoops} />
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <Insights insights={insights} />
            <Recommendations items={recommendations} />
          </div>

          <QuickChat prompts={quickChatPrompts} />

          <section className="rounded-[28px] border border-stone-200 bg-white p-6 text-sm leading-6 text-stone-600 shadow-soft">
            <p className="font-semibold text-stone-950">Morning briefing mindset</p>
            <p className="mt-3">
              This Daily OS front layer is built with mock data only so you can focus on the experience without any backend calls.
            </p>
          </section>
        </DailyLayout>
      </div>
    </main>
  );
}
