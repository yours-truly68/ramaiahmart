"use client";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { api, ApiError } from "@/lib/api/client";
import type { Post } from "@/lib/api/types";
import { Badge, Button, Skeleton } from "@/components/ui";
import { Dialog } from "./dialog";
import { ListingImage, priceLabel, relativeTime } from "./presentation";

export function DetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const query = useQuery({ queryKey: ["post", id], queryFn: ({ signal }) => api<Post>(`posts/${id}`, { signal }) });
  return <Dialog title="A find from campus" onClose={onClose}>
    {query.isPending ? <div className="detail-loading" aria-busy="true" aria-label="Loading post"><Skeleton shape="image" /><Skeleton /><Skeleton /></div> : query.isError ? <div className="panel-intro" role="alert"><p>{query.error instanceof ApiError && query.error.status === 404 ? "This post is no longer available. There may be another find waiting in the feed." : "We couldn’t load this post. Please try again."}</p><Button onClick={() => query.refetch()}>Try again</Button></div> : <article className="post-detail">
      <ListingImage post={query.data} detail /><div className="detail-kicker"><Badge tone={query.data.type === "OFFER" ? "offer" : "request"}>{query.data.type}</Badge><span>{query.data.category.name}</span></div>
      <h3>{query.data.title}</h3><p className="detail-price">{priceLabel(query.data)} <small>{query.data.price_unit}{query.data.type === "REQUEST" && query.data.price !== null ? " · budget" : ""}</small></p>
      <p className="post-description">{query.data.description}</p>
      <div className="post-author"><strong>{query.data.author.name}</strong>{query.data.author.university_verified && <span><CheckCircle2 size={15} aria-hidden="true" /> Verified Ramaiah student</span>}<time dateTime={query.data.created_at}>{relativeTime(query.data.created_at)}</time></div>
      <p className="panel-note">Student-to-student conversations are coming in a future release.</p>
    </article>}
  </Dialog>;
}
