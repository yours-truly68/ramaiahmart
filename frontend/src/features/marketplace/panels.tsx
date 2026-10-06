"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Pencil, Trash2, XCircle } from "lucide-react";
import { api, ApiError, errorMessage } from "@/lib/api/client";
import { useSession } from "@/lib/auth/session";
import type { Post } from "@/lib/api/types";
import { Badge, Button, Skeleton, StatusBadge } from "@/components/ui";
import { Dialog } from "./dialog";
import { ListingImage, priceLabel, relativeTime } from "./presentation";

export function DetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const [messagingNotice, setMessagingNotice] = useState(false);
  const session = useSession();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["post", id], queryFn: ({ signal }) => api<Post>(`posts/${id}`, { signal }) });

  const closePost = useMutation({
    mutationFn: () => api<Post>(`posts/${id}/close`, { method: "POST" }),
    onSuccess: (updated) => {
      client.setQueryData(["post", id], updated);
      client.invalidateQueries({ queryKey: ["my-posts"] });
      client.invalidateQueries({ queryKey: ["my-stats"] });
      client.invalidateQueries({ queryKey: ["posts"] });
    },
  });

  const deletePost = useMutation({
    mutationFn: () => api(`posts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["my-posts"] });
      client.invalidateQueries({ queryKey: ["my-stats"] });
      client.invalidateQueries({ queryKey: ["posts"] });
      onClose();
    },
  });

  const isOwner = session.data && query.data && session.data.id === query.data.author.id;

  return <Dialog title="A find from campus" onClose={onClose}>
    {query.isPending ? <div className="detail-loading" aria-busy="true" aria-label="Loading post"><Skeleton shape="image" /><Skeleton /><Skeleton /></div> : query.isError ? <div className="panel-intro" role="alert"><p>{query.error instanceof ApiError && query.error.status === 404 ? "This post is no longer available. There may be another find waiting in the feed." : "We couldn’t load this post. Please try again."}</p><Button onClick={() => query.refetch()}>Try again</Button></div> : <article className="post-detail">
      <ListingImage post={query.data} detail /><div className="detail-kicker"><Badge tone={query.data.type === "OFFER" ? "offer" : "request"}>{query.data.type}</Badge><StatusBadge status={query.data.status} /><span>{query.data.category.name}</span></div>
      <h3>{query.data.title}</h3><p className="detail-price">{priceLabel(query.data)} <small>{query.data.price_unit}{query.data.type === "REQUEST" && query.data.price !== null ? " · budget" : ""}</small></p>
      <p className="post-description">{query.data.description}</p>
      <div className="post-author"><strong>{query.data.author.name}</strong><time dateTime={query.data.created_at}>{relativeTime(query.data.created_at)}</time></div>

      {isOwner ? (
        <div className="detail-owner-actions" style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
          {["DRAFT", "REJECTED"].includes(query.data.status) && (
            <Link href={`/post/create?draft=${query.data.id}`} className="rm-button rm-button--secondary rm-button--sm">
              <Pencil size={15} /> Edit post
            </Link>
          )}
          {query.data.status === "PUBLISHED" && (
            <Button variant="secondary" size="sm" disabled={closePost.isPending} onClick={() => closePost.mutate()}>
              <XCircle size={15} /> {closePost.isPending ? "Closing…" : "Close listing"}
            </Button>
          )}
          {["DRAFT", "REJECTED", "CLOSED"].includes(query.data.status) && (
            <Button variant="destructive" size="sm" disabled={deletePost.isPending} onClick={() => { if (confirm("Delete this post permanently?")) deletePost.mutate(); }}>
              <Trash2 size={15} /> {deletePost.isPending ? "Deleting…" : "Delete post"}
            </Button>
          )}
          {(closePost.isError || deletePost.isError) && (
            <p className="form-error" role="alert">{errorMessage(closePost.error || deletePost.error)}</p>
          )}
        </div>
      ) : (
        <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border)" }}>
          <Button variant="accent" style={{ width: "100%", justifyContent: "center" }} onClick={() => setMessagingNotice(true)}>
            <MessageSquare size={17} /> Message {query.data.author.name.split(" ")[0]}
          </Button>
          {messagingNotice && (
            <div className="panel-note" role="status" style={{ marginTop: "12px", padding: "12px", background: "var(--accent-soft-orange)", borderRadius: "8px", color: "var(--foreground)" }}>
              <strong>Direct student messaging rollout:</strong>
              <p style={{ margin: "4px 0 0", fontSize: "12px" }}>
                In-app messaging between students will be unlocked in the upcoming release. Both you and {query.data.author.name} are verified Ramaiah students.
              </p>
            </div>
          )}
        </div>
      )}
    </article>}
  </Dialog>;
}
