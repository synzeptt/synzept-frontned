import { Button } from "@/components/ui/button";

export type ContinueButtonProps = {
  onClick: () => void;
  label?: string;
};

export function ContinueButton({ onClick, label = "Continue Working" }: ContinueButtonProps) {
  return (
    <div className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <Button onClick={onClick} className="w-full justify-center py-4 text-base font-semibold">
        {label}
      </Button>
    </div>
  );
}
