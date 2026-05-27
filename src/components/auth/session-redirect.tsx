"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { routeAfterAuth } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

export function SessionRedirect() {
  const router = useRouter();
  const { hydrate, isAuthenticated, isLoading, user } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !user) return;
    router.replace(routeAfterAuth(user.onboarding_state));
  }, [isAuthenticated, isLoading, router, user]);

  return null;
}
