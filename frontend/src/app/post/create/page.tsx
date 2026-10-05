import { Suspense } from "react";
import CreatePage from "@/features/posting/create-page";
export const metadata = { title: "Post something — RamaiahMart" };
export default function Page() { return <Suspense fallback={<main id="main" className="rm-container session-state">Getting your post ready…</main>}><CreatePage /></Suspense>; }
