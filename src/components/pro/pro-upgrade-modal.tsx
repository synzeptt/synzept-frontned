"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, X } from "lucide-react";
import { api, type BillingPlan, type CheckoutSession } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";
import { UpgradePlanSurface } from "./upgrade-plan-surface";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => {
      open: () => void;
      on?: (event: string, callback: (response: unknown) => void) => void;
    };
  }
}

type BillingCycle = "monthly";
type FlowState = "choosing" | "creating" | "checkout" | "success" | "failed";

type PlanOption = {
  id: BillingCycle;
  name: string;
  price: number;
  interval: string;
  savings?: string;
  recommended?: boolean;
};

type UpgradePlanExperienceProps = {
  inline?: boolean;
  onClose?: () => void;
  source?: string;
};

const defaultPlans: PlanOption[] = [
  { id: "monthly", name: "Monthly", price: 499, interval: "month", recommended: true },
];

export function ProUpgradeModal({
  open,
  onOpenChange,
  source = "upgrade_cta",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source?: string;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-stone-950/35 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Upgrade to Synzept Pro">
      <div className="relative max-h-[min(860px,calc(100dvh-2rem))] w-full max-w-5xl overflow-y-auto rounded-[32px] bg-white shadow-[0_28px_90px_rgba(28,25,23,0.22)] ring-1 ring-stone-200">
        <UpgradePlanExperience inline={false} onClose={() => onOpenChange(false)} source={source} />
      </div>
    </div>
  );
}

export function UpgradePlanExperience({ inline = false, onClose, source = "upgrade_cta" }: UpgradePlanExperienceProps) {
  const { user, refreshUser } = useAuthStore();
  const router = useRouter();
  const [state, setState] = useState<FlowState>("choosing");
  const [billingCycle] = useState<BillingCycle>("monthly");
  const [planOptions, setPlanOptions] = useState<PlanOption[]>(defaultPlans);
  const [message, setMessage] = useState<string | null>(null);
  const checkoutCompletedRef = useRef(false);

  useEffect(() => {
    api.getBilling()
      .then((overview) => {
        const proPlans = overview.plans
          .filter((plan) => plan.planType === "pro")
          .map(toPlanOption);
        if (proPlans.length) setPlanOptions(sortPlans(proPlans));
      })
      .catch(() => undefined);
  }, []);

  const activePlan = useMemo(() => planOptions.find((plan) => plan.id === billingCycle) || planOptions[0] || defaultPlans[0], [planOptions, billingCycle]);
  const isBusy = state === "creating" || state === "checkout";

  const close = () => {
    if (isBusy) return;
    setState("choosing");
    setMessage(null);
    onClose?.();
  };

  const startCheckout = async (cycle: BillingCycle = billingCycle) => {
    setState("creating");
    setMessage(null);
    checkoutCompletedRef.current = false;
    try {
      void api.trackEvent("upgrade_plan_selected", source, { billingCycle: cycle });
      const checkout = await api.createCheckout("pro");
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
      subscription_id: checkout.subscriptionId,
      prefill: { email, name },
      theme: { color: "#24231f" },
      handler: async (response: Record<string, string>) => {
        checkoutCompletedRef.current = true;
        setState("success");
        setMessage("Unlocking your workspace...");
        try {
          await api.verifyPayment({
            checkoutId: checkout.checkoutId,
            providerSubscriptionId: response.razorpay_subscription_id,
            providerPaymentId: response.razorpay_payment_id,
            providerSignature: response.razorpay_signature,
          });
          await refreshUser();
          window.dispatchEvent(new Event("synzept:billing-updated"));
          void api.trackEvent("upgrade_completed", source, { billingCycle: "monthly" });
          window.setTimeout(() => {
            onClose?.();
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
      void api.cancelCheckout(checkout.checkoutId).catch(() => undefined).finally(() => {
        setMessage("Payment wasn't completed. No Pro access was activated.");
        setState("failed");
      });
    });
    razorpay.open();
  };

  return (
    <div className={cn("w-full", inline ? "rounded-[32px] border border-stone-200/80 bg-[#fcfbf8] p-4 sm:p-8" : "rounded-[32px] border border-stone-200/80 bg-[#fcfbf8] p-5 sm:p-8")}>
      {!inline ? (
        <button type="button" onClick={close} disabled={isBusy} className="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-full text-stone-500 transition hover:bg-stone-100 disabled:opacity-40" aria-label="Close upgrade">
          <X className="h-5 w-5" />
        </button>
      ) : null}

      {state === "success" ? (
        <div className="grid min-h-[390px] place-items-center px-2 py-8 text-center">
          <div>
            <span className="mx-auto grid h-16 w-16 animate-pulse place-items-center rounded-full bg-emerald-50 text-emerald-700">
              <Sparkles className="h-8 w-8" />
            </span>
            <h2 className="mt-5 text-3xl font-semibold text-stone-950">Welcome to Synzept Pro!</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">{message || "Unlocking your workspace..."}</p>
          </div>
        </div>
      ) : (
        <UpgradePlanSurface
          billingCycle="monthly"
          setBillingCycle={() => undefined}
          activePlan={activePlan}
          isBusy={isBusy}
          state={state}
          message={message}
          onUpgrade={() => {
            void startCheckout();
          }}
        />
      )}
    </div>
  );
}

function toPlanOption(plan: BillingPlan): PlanOption {
  const id: BillingCycle = "monthly";
  return {
    id,
    name: "Monthly",
    price: plan.priceInr,
    interval: plan.interval === "year" ? "year" : "month",
    savings: plan.savings || undefined,
    recommended: true,
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
