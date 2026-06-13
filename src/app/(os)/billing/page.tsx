"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, CreditCard, RefreshCw, ShieldCheck, Sparkles, X } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { api, type BillingOverview, type CheckoutSession } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

const benefits = [
  "Synzept Agent",
  "Synzept Knows You",
  "Advanced Memory",
  "Unlimited Projects",
  "Priority Features",
];

export default function BillingPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuthStore();
  const [billing, setBilling] = useState<BillingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setMessage(null);
    try {
      setBilling(await api.getBilling());
    } catch {
      setMessage("Billing status could not load.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const upgrade = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const checkout = await api.createCheckout("pro");
      await openRazorpay(checkout, user?.email || "", user?.display_name || "");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Checkout could not start.");
      setProcessing(false);
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
      handler: async (response: Record<string, string>) => {
        try {
          const plan = await api.verifyPayment({
            checkoutId: checkout.checkoutId,
            providerOrderId: response.razorpay_order_id,
            providerPaymentId: response.razorpay_payment_id,
            providerSignature: response.razorpay_signature,
          });
          setBilling((current) => current ? { ...current, plan } : current);
          setMessage(`Plan: Pro. Subscription: Active. Renewal Date: ${formatDate(plan.renewalDate)}.`);
          await refreshUser();
          window.setTimeout(() => router.replace("/dashboard"), 1200);
        } catch (err) {
          setMessage(err instanceof Error ? err.message : "Payment verification failed. No Pro access was activated.");
          setProcessing(false);
        }
      },
      modal: {
        ondismiss: async () => {
          try {
            const plan = await api.cancelCheckout(checkout.checkoutId);
            setBilling((current) => current ? { ...current, plan } : current);
          } catch {
            /* The checkout still remains unverified, so Pro is not activated. */
          }
          setProcessing(false);
          setMessage("Payment was not completed.");
        },
      },
    };
    new window.Razorpay(options).open();
  };

  const cancel = async () => {
    setProcessing(true);
    setMessage(null);
    try {
      const plan = await api.cancelSubscription();
      setBilling((current) => current ? { ...current, plan } : current);
      await refreshUser();
      setMessage("Subscription canceled. Your account is now on Free.");
    } catch {
      setMessage("Subscription could not be canceled.");
    } finally {
      setProcessing(false);
    }
  };

  const plan = billing?.plan;
  const isPro = Boolean(plan?.isPro);

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader label="Billing" title="Synzept Pro" />
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-5 md:px-8">
        {message && <p className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700">{message}</p>}
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="rounded-lg border border-stone-900 bg-stone-950 p-6 text-white shadow-soft">
            <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
              <Sparkles className="h-3.5 w-3.5" />
              Synzept Pro
            </p>
            <h2 className="mt-3 text-4xl font-semibold">₹399/month</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">
              Stop rebuilding context. Unlock the continuity system that helps you know what matters, what is unfinished, and what to do next.
            </p>
            <div className="mt-6 grid gap-2 md:grid-cols-2">
              {benefits.map((benefit) => (
                <p key={benefit} className="flex items-center gap-2 text-sm text-stone-200">
                  <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                  {benefit}
                </p>
              ))}
            </div>
            {!isPro && (
              <Button onClick={upgrade} disabled={processing || loading} className="mt-7 bg-white text-stone-950 hover:bg-stone-100">
                <CreditCard className="mr-1.5 h-4 w-4" />
                {processing ? "Opening Razorpay..." : "Proceed To Payment"}
              </Button>
            )}
          </div>

          <aside className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
              <ShieldCheck className="h-4 w-4 text-muted" />
              Current Plan
            </p>
            <p className="mt-4 text-3xl font-semibold text-stone-950">{isPro ? "Pro" : "Free"}</p>
            <p className="mt-2 text-sm text-muted">
              {isPro ? `Renews ${formatDate(plan?.renewalDate)}` : "Upgrade to unlock Pro features."}
            </p>
            <div className="mt-5 rounded-md bg-stone-50 px-3 py-3 text-sm text-stone-700">
              <p>Plan: {isPro ? "Pro" : "Free"}</p>
              <p className="mt-1">Subscription: {plan?.status || "inactive"}</p>
              {isPro && <p className="mt-1">Renewal Date: {formatDate(plan?.renewalDate)}</p>}
              <p className="mt-1">Payment: {plan?.paymentStatus || "none"}</p>
            </div>
            {!isPro && (
              <div className="mt-4 rounded-md border border-border bg-white px-3 py-3 text-sm text-stone-700">
                <p className="font-medium text-stone-950">Payment Method</p>
                <p className="mt-1">Razorpay Checkout</p>
              </div>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="outline" onClick={load} disabled={loading}>
                <RefreshCw className="mr-1.5 h-4 w-4" />
                Refresh
              </Button>
              {isPro && (
                <Button variant="outline" onClick={cancel} disabled={processing}>
                  <X className="mr-1.5 h-4 w-4" />
                  Cancel
                </Button>
              )}
            </div>
          </aside>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="text-sm font-semibold text-stone-950">Transaction History</p>
          <div className="mt-3 divide-y divide-border">
            {(billing?.transactions || []).map((item) => (
              <div key={item.id} className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-stone-900">{item.status} - {item.provider}</p>
                  <p className="text-xs text-muted">{formatDate(item.createdAt)}</p>
                </div>
                <p className="text-stone-700">₹{item.amount} {item.currency}</p>
              </div>
            ))}
            {!billing?.transactions?.length && <p className="py-3 text-sm text-muted">No transactions yet.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

function ensureRazorpay() {
  if (window.Razorpay) return Promise.resolve();
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Razorpay checkout failed to load."));
    document.body.appendChild(script);
  });
}

function formatDate(value?: string | null) {
  if (!value) return "not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "not scheduled";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
