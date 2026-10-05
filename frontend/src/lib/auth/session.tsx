"use client";
import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, errorMessage } from "@/lib/api/client";
import type { User } from "@/lib/api/types";
import { Button, Skeleton } from "@/components/ui";

export function safeNext(value: string | null) {
  return value && /^\/(?!\/)/.test(value) && !/[\\\u0000-\u001f]/.test(value) && !/^\/(login|register)([/?#]|$)/.test(value) ? value : "/profile";
}
export function useSession() {
  return useQuery({ queryKey: ["me"], queryFn: async ({ signal }) => {
    try { return await api<User>("users/me", { signal }); }
    catch (error) { if (error instanceof ApiError && error.status === 401) return null; throw error; }
  }, retry: false, staleTime: 15000, refetchOnWindowFocus: true });
}
export function SessionBoundary({ next, children }: { next: string; children: (user: User) => ReactNode }) {
  const session = useSession();
  useEffect(() => { if (!session.isPending && !session.data) document.getElementById("session-heading")?.focus(); }, [session.isPending, session.data]);
  if (session.isPending) return <main id="main" className="rm-container session-state" aria-busy="true" aria-label="Checking your session"><Skeleton shape="circle" /><Skeleton /><Skeleton /><Skeleton shape="image" /></main>;
  if (session.isError) return <main id="main" className="rm-container session-state"><h1 id="session-heading" tabIndex={-1}>Let’s reconnect.</h1><p role="alert">{errorMessage(session.error)}</p><Button onClick={() => session.refetch()}>Try again</Button></main>;
  if (!session.data) return <main id="main" className="rm-container session-state"><p className="eyebrow">Your corner of campus</p><h1 id="session-heading" tabIndex={-1}>A little hello<br />before you continue.</h1><p>Log in to see your profile or post something for campus.</p><Link className="rm-button rm-button--accent rm-button--md" href={`/login?next=${encodeURIComponent(next)}`}>Log in to continue</Link><Link href={`/register?next=${encodeURIComponent(next)}`}>New here? Create an account</Link></main>;
  return children(session.data);
}
