"use client";

import Link from "next/link";
import type { ComponentProps } from "react";
import { api } from "@/lib/api";

type TrackedLinkProps = ComponentProps<typeof Link> & {
  eventType: string;
  surface?: string;
  metadata?: Record<string, unknown>;
};

export function TrackedLink({ eventType, surface, metadata, onClick, ...props }: TrackedLinkProps) {
  return (
    <Link
      {...props}
      onClick={(event) => {
        void api.trackEvent(eventType, surface, metadata);
        onClick?.(event);
      }}
    />
  );
}
