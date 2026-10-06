import type { Metadata } from "next";
import "./globals.css";
import "@/features/marketplace/home.css";
import "@/features/account/account.css";
import { RouteTransition } from "@/components/route-transition";
import { Providers } from "./providers";
import { CookieBanner } from "@/components/legal/cookie-banner";
import { CookieModal } from "@/components/legal/cookie-modal";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://ramaiahmart.com";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "RamaiahMart — The stuff you need. Already on campus.",
    template: "%s — RamaiahMart",
  },
  description:
    "Buy, sell, rent, borrow, and find useful things from fellow Ramaiah students. The secure, verified campus marketplace for MSRIT.",
  applicationName: "RamaiahMart",
  authors: [{ name: "RamaiahMart Student Community" }],
  generator: "Next.js",
  keywords: [
    "RamaiahMart",
    "MSRIT",
    "Ramaiah Institute of Technology",
    "campus marketplace",
    "college marketplace",
    "student buy and sell",
    "engineering textbooks",
    "used electronics Bangalore",
    "student accommodation items",
  ],
  referrer: "origin-when-cross-origin",
  creator: "RamaiahMart",
  publisher: "RamaiahMart",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "RamaiahMart — The stuff you need. Already on campus.",
    description:
      "Buy, sell, rent, borrow, and find useful things from fellow Ramaiah students. The secure, verified campus marketplace for MSRIT.",
    url: siteUrl,
    siteName: "RamaiahMart",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "RamaiahMart — Campus Marketplace for Ramaiah Students",
      },
    ],
    locale: "en_IN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "RamaiahMart — The stuff you need. Already on campus.",
    description:
      "Buy, sell, rent, borrow, and find useful things from fellow Ramaiah students.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Providers>
          <RouteTransition>{children}</RouteTransition>
          <CookieBanner />
          <CookieModal />
        </Providers>
      </body>
    </html>
  );
}
