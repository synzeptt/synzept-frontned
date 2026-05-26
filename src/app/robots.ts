import type { MetadataRoute } from "next";

import { absoluteUrl, getSiteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/early-access", "/login", "/signup"],
        disallow: ["/api/", "/dashboard", "/chat", "/projects", "/notes", "/tasks", "/settings", "/help", "/onboarding"],
      },
    ],
    sitemap: absoluteUrl("/sitemap.xml"),
    host: getSiteUrl(),
  };
}
