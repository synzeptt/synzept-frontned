import type { Metadata } from "next";

export const SITE_NAME = "Synzept";
export const SITE_DESCRIPTION = "Synzept is a continuity-first AI workspace for ongoing life and work.";
export const SITE_URL = "https://synzept.com";
export const SITE_KEYWORDS = [
  "continuity-first AI workspace",
  "memory-powered organization",
  "ongoing work continuity",
  "AI workspace",
  "organizational intelligence",
];

export const SOCIAL_PROFILES = [
  { label: "LinkedIn", href: "https://www.linkedin.com/company/synzeptb2b/?lipi=urn%3Ali%3Apage%3Ad_flagship3_search_srp_all%3BqnUtWPZySyeB73pbReMXBA%3D%3D" },
  { label: "Instagram", href: "https://www.instagram.com/synzept.ai/" },
  { label: "Facebook", href: "https://www.facebook.com/SynzeptLLC" },
  { label: "YouTube", href: "https://www.youtube.com/@Synzeptt" },
  { label: "X", href: "https://x.com/Synzeptt" },
] as const;

export function getSiteUrl() {
  return SITE_URL;
}

export function absoluteUrl(path: string) {
  return new URL(path, getSiteUrl()).toString();
}

export function createPageMetadata({
  title,
  description = SITE_DESCRIPTION,
  path = "/",
  noIndex = false,
  imagePath = "/opengraph-image",
}: {
  title: string;
  description?: string;
  path?: string;
  noIndex?: boolean;
  imagePath?: string;
}): Metadata {
  const url = absoluteUrl(path);
  const image = absoluteUrl(imagePath);
  return {
    title,
    description,
    keywords: SITE_KEYWORDS,
    alternates: { canonical: url },
    robots: noIndex ? { index: false, follow: false, nocache: true } : { index: true, follow: true, nocache: true },
    openGraph: {
      title,
      description,
      url,
      siteName: SITE_NAME,
      type: "website",
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: `${SITE_NAME} preview image`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [image],
    },
  };
}

export function createRootMetadata(): Metadata {
  return {
    title: {
      default: SITE_NAME,
      template: `%s | ${SITE_NAME}`,
    },
    description: SITE_DESCRIPTION,
    applicationName: SITE_NAME,
    keywords: SITE_KEYWORDS,
    metadataBase: new URL(getSiteUrl()),
    openGraph: {
      title: SITE_NAME,
      description: SITE_DESCRIPTION,
      url: getSiteUrl(),
      siteName: SITE_NAME,
      type: "website",
      images: [absoluteUrl("/opengraph-image")],
    },
    twitter: {
      card: "summary_large_image",
      title: SITE_NAME,
      description: SITE_DESCRIPTION,
      images: [absoluteUrl("/opengraph-image")],
    },
    icons: {
      icon: [
        { url: "/favicon.ico" },
        { url: "/favicon-16.png", sizes: "16x16", type: "image/png" },
        { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
        { url: "/favicon-48.png", sizes: "48x48", type: "image/png" },
      ],
      apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    },
    manifest: "/site.webmanifest",
    authors: [{ name: SITE_NAME }],
    creator: SITE_NAME,
    publisher: SITE_NAME,
  };
}

export function buildStructuredData() {
  const siteUrl = getSiteUrl();
  return [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: SITE_NAME,
      url: siteUrl,
      description: SITE_DESCRIPTION,
      logo: absoluteUrl("/synzept-logo.png"),
      sameAs: SOCIAL_PROFILES.map((item) => item.href),
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: SITE_NAME,
      url: siteUrl,
      description: SITE_DESCRIPTION,
      inLanguage: "en",
    },
    {
      "@context": "https://schema.org",
      "@type": "Product",
      name: SITE_NAME,
      description: SITE_DESCRIPTION,
      brand: {
        "@type": "Organization",
        name: SITE_NAME,
      },
      category: "Productivity software",
      url: siteUrl,
    },
  ];
}
