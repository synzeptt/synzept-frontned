"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, CreditCard, Loader2, Sparkles, X } from "lucide-react";
import { api, type BillingPlan, type CheckoutSession } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
      on?: (event: string, callback: (response: unknown) => void) => void;
    };
  }
}

type BillingCycle = "monthly" | "yearly";
type FlowState = "choosing" | "creating" | "checkout" | "success" | "failed";

const features = [
  "Synzept Agent",
  "Synzept Knows You",
  "Advanced Memory",
  "Unlimited Projects",
  "Priority Features",
];

const defaultPlans: PlanOption[] = [
  { id: "monthly", name: "Monthly", price: 399, interval: "month" },
  { id: "yearly", name: "Yearly", price: 3999, interval: "year", savings: "Save ₹789", recommended: true },
];

type PlanOption = {
  id: BillingCycle;
  name: string;
  price: number;
  interval: string;
  savings?: string;
  recommended?: boolean;
};

export function ProUpgradeModal({
  open,
  onOpenChange,
  source = "upgrade_cta",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source?: string;
}) {
  const { user, refreshUser } = useAuthStore();
  const router = useRouter();
  const [state, setState] = useState<FlowState>("choosing");
  const [selectedPlan, setSelectedPlan] = useState<BillingCycle>("yearly");
  const [planOptions, setPlanOptions] = useState<PlanOption[]>(defaultPlans);
  const [message, setMessage] = useState<string | null>(null);
  const checkoutCompletedRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    api.getBilling()
      .then((overview) => {
        const proPlans = overview.plans
          .filter((plan) => plan.planType === "pro")
          .map(toPlanOption);
        if (proPlans.length) setPlanOptions(sortPlans(proPlans));
      })
      .catch(() => undefined);
  }, [open]);

  const activePlan = useMemo(() => planOptions.find((plan) => plan.id === selectedPlan) || planOptions[0] || defaultPlans[1], [planOptions, selectedPlan]);

  if (!open) return null;

  const close = () => {
    if (state === "creating" || state === "checkout") return;
    setState("choosing");
    setMessage(null);
    onOpenChange(false);
  };

  const startCheckout = async (billingCycle: BillingCycle = selectedPlan) => {
    setSelectedPlan(billingCycle);
    setState("creating");
    setMessage(null);
    checkoutCompletedRef.current = false;
    try {
      void api.trackEvent("upgrade_plan_selected", source, { billingCycle });
      const checkout = await api.createCheckout("pro", billingCycle);
      setState("checkout");
      await openRazorpay(checkout, user?.email || "", user?.display_name || "");
    } catch (err) {
      const text = err instanceof Error ? err.message : "Payment could not start.";
      if (/sign in|session/i.test(text)) {
        router.push("/login");
        return;
      }
      setMessage(text);
      setState("failed");
    }
  };

  const openRazorpay = async (checkout: CheckoutSession, email: string, name: string) => {
    await ensureRazorpay();
    if (!window.Razorpay || !checkout.keyId) {
      throw new Error("Payment checkout is unavailable.");
    }

    const options = {
      key: checkout.keyId,
      amount: checkout.amount,
      currency: checkout.currency,
      name: "Synzept",
      description: checkout.description,
      order_id: checkout.orderId,
      prefill: { email, name },
      theme: { color: "#24231f" },
      handler: async (response: Record<string, string>) => {
        checkoutCompletedRef.current = true;
        setState("success");
        setMessage("Unlocking your workspace...");
        try {
          await api.verifyPayment({
            checkoutId: checkout.checkoutId,
            providerOrderId: response.razorpay_order_id,
            providerPaymentId: response.razorpay_payment_id,
            providerSignature: response.razorpay_signature,
          });
          await refreshUser();
          void api.trackEvent("upgrade_completed", source, { billingCycle: checkout.billingCycle || selectedPlan });
          window.setTimeout(() => {
            onOpenChange(false);
            setState("choosing");
            setMessage(null);
          }, 1400);
        } catch (err) {
          setMessage(err instanceof Error ? err.message : "Payment verification failed. No Pro access was activated.");
          setState("failed");
        }
      },
      modal: {
        ondismiss: async () => {
          if (checkoutCompletedRef.current) return;
          await api.cancelCheckout(checkout.checkoutId).catch(() => undefined);
          setMessage("Payment wasn't completed.");
          setState("failed");
        },
      },
    };

    const razorpay = new window.Razorpay(options);
    razorpay.on?.("payment.failed", () => {
      checkoutCompletedRef.current = false;
      setMessage("Payment wasn't completed.");
      setState("failed");
    });
    razorpay.open();
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-stone-950/35 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Upgrade to Synzept Pro">
      <div className="relative max-h-[min(720px,calc(100dvh-2rem))] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-[0_28px_90px_rgba(28,25,23,0.22)] ring-1 ring-stone-200">
        <button type="button" onClick={close} disabled={state === "creating" || state === "checkout"} className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-lg text-stone-500 hover:bg-stone-100 disabled:opacity-40" aria-label="Close upgrade">
          <X className="h-4 w-4" />
        </button>

        {state === "success" ? (
          <div className="grid min-h-[420px] place-items-center p-8 text-center">
            <div>
              <span className="mx-auto grid h-16 w-16 animate-pulse place-items-center rounded-full bg-emerald-50 text-emerald-700">
                <Sparkles className="h-8 w-8" />
              </span>
              <h2 className="mt-5 text-3xl font-semibold text-stone-950">Welcome to Synzept Pro!</h2>
              <p className="mt-3 text-sm leading-6 text-stone-600">{message || "Unlocking your workspace..."}</p>
            </div>
          </div>
        ) : (
          <div className="p-5 sm:p-6">
            <div className="max-w-2xl">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#eef4ef] px-3 py-1 text-xs font-semibold text-[#31563d]">
                <Sparkles className="h-3.5 w-3.5" />
                Synzept Pro
              </p>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight text-stone-950">Choose a plan. Start checkout instantly.</h2>
              <p className="mt-3 text-sm leading-6 text-stone-600">Unlock continuity, memory, unlimited projects, and priority features without leaving your workspace.</p>
            </div>

            {state === "failed" && (
              <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="text-sm font-semibold text-amber-950">Payment wasn&apos;t completed.</p>
                <p className="mt-1 text-sm text-amber-800">{message || "You can try again with the same plan."}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => startCheckout(selectedPlan)} className="inline-flex h-9 items-center justify-center rounded-lg bg-stone-950 px-3 text-sm font-semibold text-white hover:bg-stone-800">
                    Try Again
                  </button>
                  <button type="button" onClick={close} className="inline-flex h-9 items-center justify-center rounded-lg border border-stone-200 bg-white px-3 text-sm font-medium text-stone-700 hover:bg-stone-50">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {planOptions.map((plan) => {
                const active = activePlan.id === plan.id;
                const busy = (state === "creating" || state === "checkout") && selectedPlan === plan.id;
                return (
                  <button
                    key={plan.id}
                    type="button"
                    disabled={state === "creating" || state === "checkout"}
                    onClick={() => startCheckout(plan.id)}
                    className={cn(
                      "relative rounded-lg border p-5 text-left transition hover:-translate-y-0.5 hover:shadow-[0_16px_45px_rgba(28,25,23,0.08)] disabled:translate-y-0 disabled:opacity-80",
                      active ? "border-stone-950 bg-stone-950 text-white" : "border-stone-200 bg-white text-stone-950 hover:border-stone-300",
                    )}
                  >
                    {plan.recommended ? (
                      <span className={cn("absolute right-4 top-4 rounded-full px-2.5 py-1 text-xs font-semibold", active ? "bg-white text-stone-950" : "bg-[#eef4ef] text-[#31563d]")}>Recommended</span>
                    ) : null}
                    <p className={cn("text-sm font-semibold", active ? "text-stone-200" : "text-stone-500")}>{plan.name}</p>
                    <div className="mt-4 flex items-end gap-2">
                      <p className="text-4xl font-semibold">₹{plan.price}</p>
                      <p className={cn("pb-1 text-sm", active ? "text-stone-300" : "text-stone-500")}>/{plan.interval}</p>
                    </div>
                    {plan.savings ? <p className={cn("mt-2 text-sm font-medium", active ? "text-emerald-200" : "text-[#31563d]")}>{plan.savings}</p> : <p className={cn("mt-2 text-sm", active ? "text-stone-300" : "text-stone-500")}>Flexible monthly billing</p>}
                    <div className="mt-5 space-y-2">
                      {features.slice(0, 4).map((feature) => (
                        <p key={feature} className={cn("flex items-center gap-2 text-sm", active ? "text-stone-100" : "text-stone-700")}>
                          <CheckCircle2 className={cn("h-4 w-4", active ? "text-emerald-200" : "text-[#3f5f4a]")} />
                          {feature}
                        </p>
                      ))}
                    </div>
                    <span className={cn("mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg text-sm font-semibold", active ? "bg-white text-stone-950" : "bg-stone-950 text-white")}>
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
                      {busy ? "Opening Razorpay..." : "Select and Pay"}
                    </span>
                  </button>
                );
              })}
            </div>

            <p className="mt-4 text-center text-xs text-stone-500">Secure checkout powered by Razorpay. Pro activates automatically after verification.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function toPlanOption(plan: BillingPlan): PlanOption {
  const id: BillingCycle = plan.billingCycle === "yearly" || plan.interval === "year" ? "yearly" : "monthly";
  return {
    id,
    name: id === "yearly" ? "Yearly" : "Monthly",
    price: plan.priceInr,
    interval: plan.interval === "year" ? "year" : "month",
    savings: plan.savings || undefined,
    recommended: id === "yearly",
  };
}

function sortPlans(plans: PlanOption[]) {
  return plans.slice().sort((a, b) => (a.id === "monthly" ? -1 : 1) - (b.id === "monthly" ? -1 : 1));
}

function ensureRazorpay() {
  if (window.Razorpay) return Promise.resolve();
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Razorpay checkout failed to load.")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Razorpay checkout failed to load."));
    document.body.appendChild(script);
  });
}
