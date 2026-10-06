import type { Metadata } from "next";
import { Suspense } from "react";
import CreatePage from "@/features/posting/create-page";

export const metadata: Metadata = {
  title: "Create a listing",
  description: "Post an item to offer or request from fellow Ramaiah students.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function Page() {
  return (
    <Suspense
      fallback={
        <main id="main" className="rm-container session-state">
          Getting your post ready…
        </main>
      }
    >
      <CreatePage />
    </Suspense>
  );
}
