"use client";

import { useEffect, useState, type ComponentType } from "react";
import { Apple, Check, Home, Share, Smartphone, X } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const ANDROID_DOWNLOAD_URL = process.env.NEXT_PUBLIC_ANDROID_APK_URL || "/downloads/synzept.apk";

const IPHONE_STEPS: Array<{
  title: string;
  text: string;
  icon: ComponentType<{ className?: string }>;
}> = [
  {
    title: "Open in Safari",
    text: "Use Safari on your iPhone for the best installation support.",
    icon: Apple,
  },
  {
    title: "Tap Share",
    text: "Tap the Share button in the Safari toolbar.",
    icon: Share,
  },
  {
    title: "Tap Add to Home Screen",
    text: "Choose Add to Home Screen from the share sheet.",
    icon: Smartphone,
  },
  {
    title: "Tap Add",
    text: "Confirm the Synzept name and icon.",
    icon: Check,
  },
  {
    title: "Launch Synzept from Home Screen",
    text: "Open Synzept from your iPhone home screen like an app.",
    icon: Home,
  },
];

export function MobileDownloadCta({ className, compact = false }: { className?: string; compact?: boolean }) {
  const [showAndroidInstall, setShowAndroidInstall] = useState(false);
  const [showIphoneInstall, setShowIphoneInstall] = useState(false);
  const size = compact ? "default" : "lg";

  useEffect(() => {
    if (!showAndroidInstall && !showIphoneInstall) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setShowAndroidInstall(false);
        setShowIphoneInstall(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [showAndroidInstall, showIphoneInstall]);

  return (
    <>
      <div className={cn("grid gap-3 sm:max-w-md", className)}>
        {ANDROID_DOWNLOAD_URL ? (
          <a
            href={ANDROID_DOWNLOAD_URL}
            download
            className={cn(buttonVariants({ size }), "gap-2")}
            aria-label="Download Synzept Android APK"
          >
            <Smartphone className="h-4 w-4" />
            Download for Android
          </a>
        ) : (
          <Button
            type="button"
            size={size}
            className="gap-2"
            onClick={() => setShowAndroidInstall(true)}
            aria-haspopup="dialog"
          >
            <Smartphone className="h-4 w-4" />
            Download for Android
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size={size}
          className="gap-2"
          onClick={() => setShowIphoneInstall(true)}
          aria-haspopup="dialog"
        >
          <Apple className="h-4 w-4" />
          Download for iPhone
        </Button>
      </div>

      <AndroidInstallModal open={showAndroidInstall} onClose={() => setShowAndroidInstall(false)} />
      <IphoneInstallModal open={showIphoneInstall} onClose={() => setShowIphoneInstall(false)} />
    </>
  );
}

function AndroidInstallModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-stone-950/50 px-4 py-4 backdrop-blur-sm animate-fade-in sm:items-center"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-white/70 bg-white p-5 text-left shadow-2xl sm:p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="android-install-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Android download</p>
            <h2 id="android-install-title" className="mt-2 text-2xl font-semibold text-stone-950">
              Android APK is not published yet
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              A valid Synzept APK must be uploaded and configured before Android downloads can start from this page.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border text-stone-500 transition hover:bg-stone-50 hover:text-stone-950"
            aria-label="Close Android download status"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function IphoneInstallModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-stone-950/50 px-4 py-4 backdrop-blur-sm animate-fade-in sm:items-center"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-white/70 bg-white p-5 text-left shadow-2xl sm:p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="iphone-install-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border pb-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">iPhone installation</p>
            <h2 id="iphone-install-title" className="mt-2 text-2xl font-semibold text-stone-950">
              Install Synzept on iPhone
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Synzept installs as a home screen app from Safari. No sign in is required to view these steps.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border text-stone-500 transition hover:bg-stone-50 hover:text-stone-950"
            aria-label="Close iPhone installation instructions"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5 grid gap-3">
          {IPHONE_STEPS.map((step, index) => (
            <InstallStep key={step.title} index={index + 1} {...step} />
          ))}
        </div>
      </div>
    </div>
  );
}

function InstallStep({
  index,
  title,
  text,
  icon: Icon,
}: {
  index: number;
  title: string;
  text: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-border bg-surface p-3">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-stone-950 text-white shadow-soft">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">Step {index}</p>
        <h3 className="mt-1 text-sm font-semibold text-stone-950">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p>
      </div>
    </div>
  );
}

export function MobileDownloadShowcase() {
  return (
    <section id="download" className="border-y border-border bg-white">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="mx-auto max-w-md text-center">
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Mobile app</p>
          <h2 className="mt-3 text-3xl font-semibold sm:text-4xl">Download Synzept</h2>
          <MobileDownloadCta className="mt-8" compact />
        </div>
      </div>
    </section>
  );
}
