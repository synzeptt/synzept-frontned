import Image from "next/image";

import { cn } from "@/lib/cn";

type BrandLogoProps = {
  className?: string;
  imageClassName?: string;
  priority?: boolean;
};

export function BrandLogo({ className, imageClassName, priority = false }: BrandLogoProps) {
  return (
    <span className={cn("inline-flex items-center", className)} aria-label="Synzept">
      <Image
        src="/synzept-logo.png"
        alt="Synzept"
        width={487}
        height={125}
        priority={priority}
        className={cn("block h-8 w-auto object-contain", imageClassName)}
      />
    </span>
  );
}
