import type { Metadata } from "next";

import { createPageMetadata, SITE_DESCRIPTION } from "@/lib/seo";

export const metadata: Metadata = createPageMetadata({
  title: "Early access",
  description: SITE_DESCRIPTION,
  path: "/early-access",
});

export default function EarlyAccessLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
