import { cn } from "@/lib/cn";

export function initialsFor(name?: string | null, email?: string | null) {
  const source = (name || email || "Synzept").trim();
  const parts = source.includes("@") ? [source[0]] : source.split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function Avatar({
  name,
  email,
  src,
  size = "md",
  className,
}: {
  name?: string | null;
  email?: string | null;
  src?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizeClass = size === "lg" ? "h-16 w-16 text-lg" : size === "sm" ? "h-9 w-9 text-xs" : "h-11 w-11 text-sm";

  return (
    <div
      className={cn(
        "grid shrink-0 place-items-center overflow-hidden rounded-full border border-border bg-accent-muted font-semibold text-accent-foreground",
        sizeClass,
        className,
      )}
      aria-hidden="true"
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />
      ) : (
        <span>{initialsFor(name, email)}</span>
      )}
    </div>
  );
}
