"use client";

import { useEffect, useState } from "react";
import { CreditCard, Download, RefreshCw, ShieldCheck, Sparkles, X } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { api, type BillingOverview } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

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
    <div className="h-full overflow-y-auto">
      <PageHeader label="Billing" title="Manage Synzept Pro" />
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-5 md:px-8">
        {message && <p className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700">{message}</p>}

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="rounded-lg border border-border bg-white p-6 shadow-soft">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              <Sparkles className="h-3.5 w-3.5" />
              Current Plan
            </p>
            <h2 className="mt-3 text-4xl font-semibold text-stone-950">{isPro ? "Synzept Pro" : "Free"}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
              {isPro
                ? "Your Pro workspace is active. Manage renewal, transaction history, and subscription controls from this page."
                : "You are currently on the Free plan. Upgrades now start directly from the Upgrade to Pro button in the app."}
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <StatusTile label="Plan" value={isPro ? "Pro" : "Free"} />
              <StatusTile label="Renewal Date" value={isPro ? formatDate(plan?.renewalDate) : "Not scheduled"} />
              <StatusTile label="Payment" value={plan?.paymentStatus || "none"} />
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="outline" onClick={manageSubscription}>
                <CreditCard className="mr-1.5 h-4 w-4" />
                Manage Subscription
              </Button>
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

          <aside className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
              <ShieldCheck className="h-4 w-4 text-muted" />
              Billing Status
            </p>
            <div className="mt-5 rounded-md bg-stone-50 px-3 py-3 text-sm text-stone-700">
              <p>Plan: {isPro ? "Pro" : "Free"}</p>
              <p className="mt-1">Subscription: {plan?.status || "inactive"}</p>
              <p className="mt-1">Renewal Date: {isPro ? formatDate(plan?.renewalDate) : "not scheduled"}</p>
              <p className="mt-1">Provider: {plan?.provider || "manual"}</p>
            </div>
            <p className="mt-4 text-xs leading-5 text-muted">
              Checkout now happens directly from the Upgrade to Pro button. Billing is only for subscription management and history.
            </p>
          </aside>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
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
    </div>
  );
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-stone-50 p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-sm font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "not scheduled";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
