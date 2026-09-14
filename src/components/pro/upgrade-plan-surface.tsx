"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Bot, BrainCircuit, Clock3, CreditCard, Headphones, Layers3, Loader2, MessageSquareText, ShieldCheck, Sparkles, Zap } from "lucide-react";

type BillingCycle = "monthly";

type UpgradePlanSurfaceProps = {
  billingCycle: BillingCycle;
  setBillingCycle: (cycle: BillingCycle) => void;
  activePlan: {
    name: string;
    price: number;
    interval: string;
    savings?: string;
    recommended?: boolean;
  };
  isBusy: boolean;
  onUpgrade: () => void;
  state: "choosing" | "creating" | "checkout" | "success" | "failed";
  message?: string | null;
};

const featureHighlights = [
  {
    title: "Deep memory",
    description: "Keep long-term context across your work, decisions, and routines.",
    icon: BrainCircuit,
  },
  {
    title: "Premium intelligence",
    description: "Get sharper answers and more helpful guidance in every session.",
    icon: Sparkles,
  },
  {
    title: "Faster responses",
    description: "Spend less time waiting and more time moving your work forward.",
    icon: Zap,
  },
  {
    title: "Connected workflows",
    description: "Bring your tools, space, and context together in one operating layer.",
    icon: Layers3,
  },
  {
    title: "Daily clarity",
    description: "Start every day with a focused view of priorities and progress.",
    icon: Clock3,
  },
  {
    title: "Priority support",
    description: "Get faster help when you need it most.",
    icon: Headphones,
  },
];

const planHighlights = [
  { title: "Unlimited conversations", description: "Keep the conversation going without hitting limits.", icon: MessageSquareText },
  { title: "Context-rich memory", description: "Build a stronger, more personal operating system over time.", icon: ShieldCheck },
  { title: "Smarter automation", description: "Unlock more proactive help and better AI collaboration.", icon: Bot },
];

export function UpgradePlanSurface({
  billingCycle,
  setBillingCycle,
  activePlan,
  isBusy,
  onUpgrade,
  state,
  message,
}: UpgradePlanSurfaceProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col">
      <div className="mx-auto max-w-3xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">
          <Sparkles className="h-3.5 w-3.5" />
          Synzept Pro
        </div>
        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-stone-950 sm:text-4xl">
          Upgrade to Synzept Pro
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-stone-600 sm:text-base">
          Unlock a more intelligent workspace with deeper memory, richer context, and premium AI workflows.
        </p>

        <p className="mx-auto mt-8 inline-flex rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700">Monthly billing</p>
      </div>

      {state === "failed" ? (
        <div className="mt-6 rounded-[24px] border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">Payment wasn&apos;t completed.</p>
          <p className="mt-1 text-amber-800">{message || "You can try again with the same plan."}</p>
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <motion.article
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.24, ease: [0.22, 1, 0.36, 1] }}
          className="relative overflow-hidden rounded-[32px] border border-stone-200/80 bg-gradient-to-br from-stone-950 via-stone-900 to-stone-950 p-7 text-white shadow-[0_28px_90px_rgba(15,23,42,0.18)] sm:p-8"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.16),_transparent_40%)]" />
          <div className="relative">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">Synzept Pro</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-[-0.02em]">Premium access</h3>
                <p className="mt-2 max-w-xs text-sm leading-6 text-stone-300">
                  The premium operating layer for your most important work.
                </p>
              </div>
              <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-200">
                Most Popular
              </span>
            </div>

            <div className="mt-8 flex items-end gap-3">
              <p className="text-5xl font-semibold tracking-[-0.04em]">₹{activePlan.price}</p>
              <p className="pb-1 text-sm text-stone-300">/ month</p>
            </div>
            <p className="mt-2 text-sm text-stone-400">
              Billed monthly. Cancel anytime.
            </p>

            <motion.button
              whileHover={{ y: -1, scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              type="button"
              disabled={isBusy}
              onClick={onUpgrade}
              className="mt-8 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-white px-4 text-sm font-semibold text-stone-950 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
              {isBusy ? "Opening Razorpay..." : "Upgrade Now"}
            </motion.button>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {planHighlights.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="rounded-[20px] border border-white/10 bg-white/5 p-3">
                    <div className="flex items-start gap-2">
                      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      <div>
                        <p className="text-sm font-semibold text-white">{feature.title}</p>
                        <p className="mt-1 text-sm leading-6 text-stone-300">{feature.description}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.24, delay: 0.04, ease: [0.22, 1, 0.36, 1] }}
          className="rounded-[32px] border border-stone-200/80 bg-white p-7 shadow-[0_16px_44px_rgba(15,23,42,0.05)] sm:p-8"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">What you unlock</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Everything in one premium layer</h3>
            </div>
            <span className="rounded-full bg-stone-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-600">
              Included
            </span>
          </div>

          <div className="mt-8 space-y-3">
            {featureHighlights.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="flex items-start gap-3 rounded-[22px] border border-stone-200/80 bg-[#fcfbf8] p-4">
                  <div className="mt-0.5 grid h-10 w-10 place-items-center rounded-2xl bg-stone-900 text-white">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-stone-900">{feature.title}</p>
                    <p className="mt-1 text-sm leading-6 text-stone-600">{feature.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.article>
      </div>

      <div className="mt-8 flex items-center justify-center rounded-[24px] border border-stone-200/80 bg-white/80 px-4 py-3 text-center text-xs text-stone-500 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
        Secure checkout powered by Razorpay. Pro activates automatically after verification.
      </div>
    </div>
  );
}
