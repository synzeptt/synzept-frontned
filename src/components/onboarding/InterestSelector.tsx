import { OptionCard } from "@/components/onboarding/OptionCard";
import type { OnboardingPreference } from "@/types/onboarding";

export type InterestSelectorProps = {
  preferences: OnboardingPreference[];
  selectedPreferences: OnboardingPreference[];
  onTogglePreference: (preference: OnboardingPreference) => void;
};

export function InterestSelector({ preferences, selectedPreferences, onTogglePreference }: InterestSelectorProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {preferences.map((preference) => (
        <OptionCard
          key={preference}
          label={preference}
          selected={selectedPreferences.includes(preference)}
          onSelect={() => onTogglePreference(preference)}
        />
      ))}
    </div>
  );
}
