import type { Metadata } from "next";
import "./globals.css";
import "@/features/marketplace/home.css";
import "@/features/account/account.css";
import { RouteTransition } from "@/components/route-transition";
import { Providers } from "./providers";
import { CookieBanner } from "@/components/legal/cookie-banner";
import { CookieModal } from "@/components/legal/cookie-modal";

export const metadata: Metadata = {
  title: "RamaiahMart — The stuff you need. Already on campus.",
  description: "Buy, sell, rent, borrow, and find useful things from fellow Ramaiah students.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">Skip to content</a>
        <Providers>
          <RouteTransition>{children}</RouteTransition>
          <CookieBanner />
          <CookieModal />
        </Providers>
      </body>
    </html>
  );
}
