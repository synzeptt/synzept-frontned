import { Input } from "@/components/ui/input";

export type QuestionCardProps = {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
};

export function QuestionCard({ label, value, placeholder, onChange }: QuestionCardProps) {
  return (
    <div className="rounded-[28px] border border-stone-200 bg-white p-6 shadow-soft">
      <label className="block text-sm font-semibold text-stone-950">
        {label}
        <Input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="mt-4"
        />
      </label>
    </div>
  );
}
