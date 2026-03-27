import type { ReactNode } from "react";
import "./globals.css";

import { NavHeader } from "@/app/components/NavHeader";

export const metadata = {
  title: "42 Training",
  description: "Triple-track self-paced preparation for 42 Lausanne",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <NavHeader />
        <div className="app-content">{children}</div>
      </body>
    </html>
  );
}
