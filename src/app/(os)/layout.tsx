import { AppShell } from "@/components/layout/app-shell";

export default function OSLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
