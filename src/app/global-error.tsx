"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    api.trackEvent("frontend_global_error", "app", {
      message: error.message,
      digest: error.digest,
    });
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main className="flex min-h-screen items-center justify-center bg-surface px-4 text-stone-950">
          <section className="w-full max-w-md rounded-md border border-border bg-white p-6 text-center">
            <h1 className="text-xl font-semibold">Synzept needs a quick refresh</h1>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              Synzept could not render this view, but your workspace data remains safe. Retry the view or return to the dashboard.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Button onClick={reset}>
                <RotateCcw className="mr-2 h-4 w-4" />
                Retry
              </Button>
              <Button variant="outline" onClick={() => (window.location.href = "/dashboard")}>
                Dashboard
              </Button>
            </div>
          </section>
        </main>
      </body>
    </html>
  );
}
