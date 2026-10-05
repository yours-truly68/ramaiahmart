"use client";

import { ViewTransition, type ReactNode } from "react";
import { usePathname } from "next/navigation";

/** Path changes animate; query parameters and hashes keep their current UI state. */
export function RouteTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <ViewTransition key={pathname} default="none" enter="route-page" exit="route-page">
    <div className="route-page">{children}</div>
  </ViewTransition>;
}
