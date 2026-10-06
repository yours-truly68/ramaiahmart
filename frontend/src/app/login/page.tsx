import type { Metadata } from "next";
import { Suspense } from "react";
import AuthPage from "@/features/account/auth-page";

export const metadata: Metadata = {
  title: "Log in",
  description:
    "Log in to RamaiahMart using your @msrit.edu student account to browse listings, post offers or requests, and chat with peers.",
  alternates: {
    canonical: "/login",
  },
  openGraph: {
    title: "Log in — RamaiahMart",
    description:
      "Log in to RamaiahMart using your verified student email to buy, sell, or rent items on campus.",
    url: "/login",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function Page() {
  return (
    <Suspense
      fallback={
        <main id="main" className="session-state rm-container">
          Getting your corner of campus ready…
        </main>
      }
    >
      <AuthPage mode="login" />
    </Suspense>
  );
}
