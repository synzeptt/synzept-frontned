import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Check,
  CheckCircle2,
  Clock3,
  FolderKanban,
  GitPullRequestArrow,
  ListChecks,
  Sparkles,
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { TrackedLink } from "@/components/analytics/tracked-link";
import { SiteFooter } from "@/components/site-footer";
import { buttonVariants } from "@/components/ui/button";
import { createPageMetadata } from "@/lib/seo";

export const metadata: Metadata = createPageMetadata({
  title: "Pricing",
  description: "Choose Free or Pro. Synzept helps you remember where you left off and continue your work with confidence.",
  path: "/pricing",
});

const freeFeatures = [
  "Synzept Agent",
  "Basic Projects",
  "Basic AI",
  "Mobile Access",
  "Basic Memory",
  "Limited Projects",
  "Limited AI Usage",
];

const proFeatures = [
  "Synzept Agent",
  "Synzept Knows You",
  "Advanced Memory",
  "Unlimited Projects",
  "Priority Features",
];

const proDetails = [
  {
    title: "Daily Brief",
    text: "Every day Synzept generates what matters today, open loops, recent progress, and a recommended next step.",
    icon: Clock3,
  },
  {
    title: "Open Loops",
    text: "Automatically identify unfinished work, pending decisions, blockers, and follow-ups.",
    icon: ListChecks,
  },
  {
    title: "Project Intelligence",
    text: "Every project includes current focus, recent activity, open decisions, open loops, and the recommended next step.",
    icon: FolderKanban,
  },
  {
    title: "Timeline",
    text: "Track progress, milestones, decisions, and important events as your work evolves.",
    icon: GitPullRequestArrow,
  },
  {
    title: "Continuity Assistant",
    text: "Ask what to do next, what you are forgetting, what changed, and where you left off.",
    icon: Brain,
  },
];

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-surface text-stone-950">
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="flex items-center gap-3" aria-label="Synzept home">
          <BrandLogo imageClassName="h-9" priority />
        </Link>
        <nav className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/" className="hidden px-3 py-2 transition hover:text-stone-950 sm:inline-block">
            Home
          </Link>
          <Link href="/login" className="px-3 py-2 transition hover:text-stone-950">
            Login
          </Link>
          <Link href="/signup" className={buttonVariants({ size: "sm" })}>
            Start Free
          </Link>
        </nav>
      </header>

      <section className="border-y border-border bg-white">
        <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8 md:py-20">
          <div className="max-w-3xl">
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Pricing</p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-normal sm:text-5xl">
              Never Lose Track Of Your Work Again.
            </h1>
            <p className="mt-5 text-lg leading-8 text-stone-600">
              Synzept remembers where you left off and helps you continue with confidence.
            </p>
          </div>

          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            <PricingCard
              name="Free"
              description="Perfect for trying Synzept."
              price="₹0"
              cadence="Start with the basics"
              features={freeFeatures}
              cta="Start Free"
              href="/signup"
            />
            <PricingCard
              name="Synzept Pro"
              description="For builders, founders, freelancers, and professionals."
              price="₹399"
              cadence="per month"
              features={proFeatures}
              cta="Upgrade To Pro"
              href="/billing"
              featured
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-16 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Pro value</p>
            <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">Synzept does not just store information.</h2>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              It helps you continue your work by making what matters, what is unfinished, and what should happen next visible.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {proDetails.map((item) => (
              <article key={item.title} className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <item.icon className="h-5 w-5 text-accent" />
                <h3 className="mt-4 text-lg font-semibold">{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-5 py-16 sm:px-8 lg:grid-cols-[1fr_0.7fr] lg:items-center">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Upgrade when ready</p>
            <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">Stop rebuilding context.</h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
              Open Synzept and instantly know what matters, what is unfinished, and what should happen next.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:justify-end">
            <TrackedLink href="/billing" eventType="upgrade_clicked" surface="pricing" metadata={{ placement: "bottom_cta" }} className={buttonVariants({ size: "lg", className: "gap-2" })}>
              Upgrade To Pro
              <ArrowRight className="h-4 w-4" />
            </TrackedLink>
            <Link href="/signup" className={buttonVariants({ variant: "outline", size: "lg" })}>
              Try Free
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}

function PricingCard({
  name,
  description,
  price,
  cadence,
  features,
  cta,
  href,
  featured = false,
}: {
  name: string;
  description: string;
  price: string;
  cadence: string;
  features: string[];
  cta: string;
  href: string;
  featured?: boolean;
}) {
  return (
    <article className={`rounded-lg border bg-white p-6 shadow-soft ${featured ? "border-stone-900" : "border-border"}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-semibold">{name}</h2>
            {featured ? (
              <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                <Sparkles className="h-3 w-3" />
                Best value
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="mt-7">
        <p className="text-4xl font-semibold tracking-normal">{price}</p>
        <p className="mt-2 text-sm text-muted-foreground">{cadence}</p>
      </div>
      <TrackedLink
        href={href}
        eventType={featured ? "upgrade_clicked" : "pricing_cta_clicked"}
        surface="pricing"
        metadata={{ placement: featured ? "plan_card" : "free_card" }}
        className={buttonVariants({
          variant: featured ? "default" : "outline",
          size: "lg",
          className: "mt-7 w-full gap-2",
        })}
      >
        {cta}
        <ArrowRight className="h-4 w-4" />
      </TrackedLink>
      <div className="mt-7 grid gap-3">
        {features.map((feature) => (
          <div key={feature} className="flex items-start gap-3 text-sm text-stone-700">
            {featured ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" /> : <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />}
            <span>{feature}</span>
          </div>
        ))}
      </div>
    </article>
  );
}
