"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 30000, retry: 1, refetchOnWindowFocus: false } } }));
  useEffect(() => {
    const expire = () => { client.setQueryData(["me"], null); client.removeQueries({ queryKey: ["my-posts"] }); client.removeQueries({ queryKey: ["my-stats"] }); };
    window.addEventListener("ramaiah:unauthorized", expire);
    return () => window.removeEventListener("ramaiah:unauthorized", expire);
  }, [client]);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
