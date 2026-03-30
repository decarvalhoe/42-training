import type { ReactNode } from "react";
import "./globals.css";

import type { Viewport } from "next";

import { AuthGuard } from "@/app/components/AuthGuard";
import { AuthProvider } from "@/app/components/AuthProvider";
import { UiPreferencesProvider } from "@/app/components/UiPreferencesProvider";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata = {
  title: "42 Training",
  description: "Triple-track self-paced preparation for 42 Lausanne",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="hacker-hud"
      data-contrast="default"
      data-density="comfortable"
      data-motion="system"
    >
      <body>
        <UiPreferencesProvider>
          <AuthProvider>
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <AuthGuard>{children}</AuthGuard>
          </AuthProvider>
        </UiPreferencesProvider>
      </body>
    </html>
  );
}
