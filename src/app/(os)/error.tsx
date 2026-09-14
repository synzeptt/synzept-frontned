"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function WorkspaceError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    void api.trackEvent("workspace_render_error", "workspace", { digest: error.digest });
  }, [error.digest]);

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 text-center shadow-sm">
        <h1 className="text-xl font-semibold tracking-[-0.02em] text-stone-950">This view needs a refresh</h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">Your workspace is safe. Try loading this view again, or return to Home.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button type="button" onClick={reset}><RotateCcw className="mr-2 h-4 w-4" />Try again</Button>
          <Button type="button" variant="outline" onClick={() => { window.location.href = "/home"; }}>Go to Home</Button>
        </div>
      </section>
    </div>
  );
}
