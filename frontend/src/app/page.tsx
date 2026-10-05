import { Suspense } from "react";
import Home, { FeedSkeleton } from "@/features/marketplace/home";
export default function Page() {
  return <Suspense fallback={<main id="main" className="rm-container home-loading"><p className="wordmark">Ramaiah<span>Mart</span></p><h1>The stuff you need.<br />Already on campus.</h1><FeedSkeleton /></main>}><Home /></Suspense>;
}
