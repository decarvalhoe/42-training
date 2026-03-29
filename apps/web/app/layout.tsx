import type { ReactNode } from "react";
import "./globals.css";

import type { Viewport } from "next";

import { AuthGuard } from "@/app/components/AuthGuard";
import { AuthProvider } from "@/app/components/AuthProvider";
import { NavHeader } from "@/app/components/NavHeader";

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
    <html lang="en">
      <body>
        <AuthProvider>
          <a href="#main-content" className="skip-link">
            Skip to main content
          </a>
          <AuthGuard header={<NavHeader />}>
            <div id="main-content" className="app-content">{children}</div>
          </AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
