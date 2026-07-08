import { cn } from "@/lib/cn";

export type OptionCardProps = {
  label: string;
  selected: boolean;
  onSelect: () => void;
};

export function OptionCard({ label, selected, onSelect }: OptionCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex h-full w-full items-center justify-center rounded-3xl border px-4 py-5 text-left transition focus:outline-none focus:ring-2 focus:ring-accent/30",
        selected
          ? "border-stone-950 bg-stone-950 text-white"
          : "border-stone-200 bg-white text-stone-950 hover:border-stone-300 hover:bg-stone-50",
      )}
    >
      <span className="text-base font-medium">{label}</span>
    </button>
  );
}
