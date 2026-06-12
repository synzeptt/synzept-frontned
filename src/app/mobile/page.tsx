"use client";

import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/brand-logo";
import { routeAfterAuth } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

export default function MobileEntryPage() {
  const router = useRouter();
  const { hydrate, isAuthenticated, isLoading, user } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated && user) {
      router.replace(routeAfterAuth(user.onboarding_state));
      return;
    }
    router.replace("/login");
  }, [isAuthenticated, isLoading, router, user]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-6 text-stone-950">
      <div className="flex flex-col items-center gap-5 text-center">
        <BrandLogo imageClassName="h-10" priority />
        <Loader2 className="h-6 w-6 animate-spin text-accent" aria-label="Opening Synzept" />
      </div>
    </main>
  );
}
