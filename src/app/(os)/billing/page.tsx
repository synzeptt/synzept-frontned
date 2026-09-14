"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CreditCard, Download, RefreshCw, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, type BillingOverview } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { Page, PageHeader, Row, Status, Metadata } from "@/components/design-system/workspace-primitives";

export default function BillingPage() {
  const { refreshUser } = useAuthStore();
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
    void load();
    const refreshBilling = () => void load();
    window.addEventListener("synzept:billing-updated", refreshBilling);
    return () => window.removeEventListener("synzept:billing-updated", refreshBilling);
  }, []);

  const cancel = async () => {
    if (!window.confirm("Cancel Synzept Pro? Your account will return to Free.")) return;
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

  const manageSubscription = () => {
    setMessage("Subscription management is available here. Use Cancel Subscription to stop Pro, or contact support for billing changes.");
  };

  const plan = billing?.plan;
  const isPro = Boolean(plan?.isPro);

  return (
    <Page>
      <div className="mx-auto max-w-3xl space-y-12 px-5 py-12 sm:px-8 sm:py-16">
      <PageHeader eyebrow="System" title="Billing" description="A clear record of your plan and subscription status." />
        {message && <p className="border-y border-stone-200 py-3 text-sm text-stone-700">{message}</p>}

        <section>
          <div className="border-y border-border/10 py-6">
            <p className="synzept-eyebrow">Your plan</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-stone-950">{isPro ? "Pro" : "Free"}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
              {isPro
                ? "Your Pro workspace is active. Manage renewal, transaction history, and subscription controls from this page."
                : "You are currently on the Free plan. Upgrades now start directly from the Upgrade to Pro button in the app."}
            </p>

            <div className="mt-6 divide-y divide-border/10 border-y border-border/10">
              <Row><span className="text-sm text-stone-700">Plan</span><Status>{isPro ? "Pro" : "Free"}</Status></Row>
              <Row><span className="text-sm text-stone-700">Renewal</span><Metadata>{isPro ? formatDate(plan?.renewalDate) : "Not scheduled"}</Metadata></Row>
              <Row><span className="text-sm text-stone-700">Payment</span><Metadata>{plan?.paymentStatus || "None"}</Metadata></Row>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="outline" onClick={manageSubscription}>
                <CreditCard className="mr-1.5 h-4 w-4" />
                Manage Subscription
              </Button>
              {!isPro && <UpgradeCta />}
              <Button variant="outline" onClick={load} disabled={loading}>
                <RefreshCw className="mr-1.5 h-4 w-4" />
                Refresh
              </Button>
              {isPro && (
                <Button variant="outline" onClick={cancel} disabled={processing}>
                  <X className="mr-1.5 h-4 w-4" />
                  Cancel Subscription
                </Button>
              )}
            </div>
          </div>

          <aside className="mt-8 border-b border-border/10 pb-6">
            <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
              <ShieldCheck className="h-4 w-4 text-muted" />
              Billing Status
            </p>
            <div className="mt-5 border-y border-border/10 py-3 text-sm text-stone-700">
              <p>Plan: {isPro ? "Pro" : "Free"}</p>
              <p className="mt-1">Subscription: {plan?.status || "inactive"}</p>
              <p className="mt-1">Renewal Date: {isPro ? formatDate(plan?.renewalDate) : "not scheduled"}</p>
              <p className="mt-1">Provider: {plan?.provider || "manual"}</p>
            </div>
            <p className="mt-4 text-xs leading-5 text-muted">
              Payments are processed by Razorpay. Pro access is activated only after the server verifies the subscription payment.
            </p>
            <p className="mt-3 text-xs leading-5 text-muted">
              <Link href="/refunds" className="underline hover:text-stone-950">Refund &amp; Cancellation</Link>
              <span className="mx-2">·</span>
              <Link href="/terms" className="underline hover:text-stone-950">Terms</Link>
            </p>
          </aside>
        </section>

        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-stone-950">Transaction History</p>
              <p className="mt-1 text-sm text-muted">Successful, canceled, and failed checkout records are preserved here.</p>
            </div>
            <Button variant="outline" onClick={() => setMessage("Transaction export is included in account data export from Settings.")}>
              <Download className="mr-1.5 h-4 w-4" />
              Export
            </Button>
          </div>
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
    </Page>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "not scheduled";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
