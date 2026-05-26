import type { Metadata } from "next";
import "./globals.css";
import { createRootMetadata } from "@/lib/seo";
import { ThemeProvider } from "@/components/theme/theme-provider";

export const metadata: Metadata = createRootMetadata();

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-scroll-behavior="smooth" data-theme="light" style={{ colorScheme: "light" }} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var appearance = localStorage.getItem("synzept-theme") || "light";
                appearance = appearance === "dark" ? "dark" : "light";
                document.documentElement.dataset.theme = appearance;
                document.documentElement.style.colorScheme = appearance;
              } catch (_) {
                document.documentElement.dataset.theme = "light";
                document.documentElement.style.colorScheme = "light";
              }
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-surface antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
