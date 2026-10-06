import type { Metadata } from "next";
import { Suspense } from "react";
import AuthPage from "@/features/account/auth-page";

export const metadata: Metadata = {
  title: "Join the community",
  description:
    "Create your RamaiahMart account with your @msrit.edu email. Join fellow Ramaiah students in exchanging textbooks, lab gear, electronics, and dorm essentials.",
  alternates: {
    canonical: "/register",
  },
  openGraph: {
    title: "Join the community — RamaiahMart",
    description:
      "Create your student account on RamaiahMart. Buy, sell, and rent on campus with peers.",
    url: "/register",
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
      <AuthPage mode="register" />
    </Suspense>
  );
}
