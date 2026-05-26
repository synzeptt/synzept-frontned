import Link from "next/link";
import { CopyrightLine } from "@/components/copyright-line";
import { SOCIAL_PROFILES } from "@/lib/seo";

type SocialLink = {
  label: string;
  href: string;
  icon: (props: { className?: string }) => React.ReactNode;
};

const socialLinks: SocialLink[] = SOCIAL_PROFILES.map((item) => ({
  label: item.label,
  href: item.href,
  icon: socialIconFor(item.label),
}));

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-white px-5 py-8 sm:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
        <div>
          <p>Synzept. Continuity-first AI workspace.</p>
          <CopyrightLine className="mt-2" />
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <Link href="/login" className="hover:text-stone-950">
              Login
            </Link>
            <Link href="/signup" className="hover:text-stone-950">
              Sign up
            </Link>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2" aria-label="Synzept social links">
          {socialLinks.map((item) => {
            const Icon = item.icon;
            return (
              <a
                key={item.label}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Synzept on ${item.label}`}
                className="grid h-9 w-9 place-items-center rounded-md border border-border bg-white text-stone-500 transition hover:border-stone-300 hover:bg-stone-50 hover:text-stone-950"
              >
                <Icon className="h-4 w-4" />
              </a>
            );
          })}
        </div>
      </div>
    </footer>
  );
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.5h4v11H3v-11Zm6.2 0h3.8v1.5h.1c.5-.9 1.8-1.9 3.7-1.9 4 0 4.7 2.6 4.7 6v5.4h-4v-4.8c0-1.2 0-2.7-1.7-2.7s-1.9 1.3-1.9 2.6v4.9h-4v-11Z" />
    </svg>
  );
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <path d="M17.5 6.5h.01" />
    </svg>
  );
}

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M14 8.5V6.7c0-.8.3-1.2 1.3-1.2H17V2.2c-.8-.1-1.7-.2-2.5-.2-2.6 0-4.5 1.6-4.5 4.5v2H7v3.7h3V22h4v-9.8h3l.6-3.7H14Z" />
    </svg>
  );
}

function YouTubeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2.5 12s0-3.4.4-5a3 3 0 0 1 2.1-2.1C6.6 4.5 12 4.5 12 4.5s5.4 0 7 .4A3 3 0 0 1 21.1 7c.4 1.6.4 5 .4 5s0 3.4-.4 5a3 3 0 0 1-2.1 2.1c-1.6.4-7 .4-7 .4s-5.4 0-7-.4A3 3 0 0 1 2.9 17c-.4-1.6-.4-5-.4-5Z" />
      <path d="m10 15 5-3-5-3v6Z" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M18.9 2h3.3l-7.3 8.3L23.5 22h-6.8l-5.3-6.9L5.3 22H2l7.8-8.9L1.6 2h7l4.8 6.3L18.9 2Zm-1.2 18h1.8L7.6 3.9h-2L17.7 20Z" />
    </svg>
  );
}

function socialIconFor(label: string) {
  if (label === "LinkedIn") return LinkedInIcon;
  if (label === "Instagram") return InstagramIcon;
  if (label === "Facebook") return FacebookIcon;
  if (label === "YouTube") return YouTubeIcon;
  return XIcon;
}
