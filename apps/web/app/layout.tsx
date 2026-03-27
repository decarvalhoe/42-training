import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "42 Training",
  description: "Triple-track self-paced preparation for 42 Lausanne",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
