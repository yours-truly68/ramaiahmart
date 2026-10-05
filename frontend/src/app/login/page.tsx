import { Suspense } from "react";
import AuthPage from "@/features/account/auth-page";
export const metadata = { title: "Log in — RamaiahMart" };
export default function Page() { return <Suspense fallback={<main id="main" className="session-state rm-container">Getting your corner of campus ready…</main>}><AuthPage mode="login" /></Suspense>; }
