"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Flag, MessageSquare, Pencil, PhoneCall, Trash2, XCircle } from "lucide-react";
import { api, ApiError, errorMessage } from "@/lib/api/client";
import { useSession } from "@/lib/auth/session";
import type { Conversation, Post, ReportReason } from "@/lib/api/types";
import { Badge, Button, Skeleton, StatusBadge } from "@/components/ui";
import { Dialog } from "./dialog";
import { ListingImage, priceLabel, relativeTime } from "./presentation";
import { isSafeWhatsAppUrl } from "@/lib/security/url";

export function DetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const router = useRouter();
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState<ReportReason>("EXPLICIT_IMAGE");
  const [reportDescription, setReportDescription] = useState("");
  const [reportSubmitting, setReportSubmitting] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(false);
  const [reportError, setReportError] = useState("");
  const session = useSession();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["post", id], queryFn: ({ signal }) => api<Post>(`posts/${id}`, { signal }) });

  const startConversation = useMutation({
    mutationFn: () => api<Conversation>(`posts/${id}/conversations`, { method: "POST" }),
    onSuccess: (conv) => {
      onClose();
      router.push(`/messages/${conv.id}`);
    },
  });

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
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <Button
              variant="accent"
              style={{ width: "100%", justifyContent: "center" }}
              disabled={startConversation.isPending}
              onClick={() => {
                if (!session.data) {
                  router.push(`/login?next=${encodeURIComponent("/messages")}`);
                  return;
                }
                startConversation.mutate();
              }}
            >
              <MessageSquare size={17} />
              {startConversation.isPending
                ? "Starting conversation…"
                : query.data.type === "OFFER"
                  ? "Message seller"
                  : "Offer this item"}
            </Button>

            {isSafeWhatsAppUrl(query.data.whatsapp_url) && (
              <a
                href={query.data.whatsapp_url!}
                target="_blank"
                rel="noopener noreferrer"
                className="rm-button rm-button--secondary rm-button--md"
                style={{ width: "100%", justifyContent: "center", textDecoration: "none" }}
              >
                <PhoneCall size={16} /> Continue on WhatsApp
              </a>
            )}
          </div>

          {startConversation.isError && (
            <p className="form-error" role="alert" style={{ marginTop: "8px" }}>
              {errorMessage(startConversation.error)}
            </p>
          )}

          <div style={{ marginTop: "12px", textAlign: "center" }}>
            <button
              type="button"
              className="text-action"
              style={{ fontSize: "13px", color: "var(--muted-foreground)", display: "inline-flex", alignItems: "center", gap: "6px" }}
              onClick={() => setReportOpen(true)}
            >
              <Flag size={14} /> Report this listing
            </button>
          </div>
        </div>
      )}

      {reportOpen && (
        <Dialog title="Report listing" onClose={() => { setReportOpen(false); setReportSuccess(false); setReportError(""); }}>
          {reportSuccess ? (
            <div className="panel-intro" role="status" style={{ textAlign: "center", padding: "16px 0" }}>
              <strong style={{ fontSize: "16px", color: "var(--foreground)", display: "block", marginBottom: "8px" }}>
                Report received
              </strong>
              <p style={{ fontSize: "14px", color: "var(--muted-foreground)", marginBottom: "16px" }}>
                Thank you for helping keep the Ramaiah campus community safe. Our moderation team has recorded this report.
              </p>
              <Button variant="secondary" onClick={() => { setReportOpen(false); setReportSuccess(false); }}>
                Done
              </Button>
            </div>
          ) : (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setReportSubmitting(true);
                setReportError("");
                try {
                  await api("reports", {
                    method: "POST",
                    body: JSON.stringify({
                      post_id: id,
                      reason: reportReason,
                      description: reportDescription.trim() || null,
                    }),
                  });
                  setReportSuccess(true);
                } catch (err) {
                  setReportError(errorMessage(err));
                } finally {
                  setReportSubmitting(false);
                }
              }}
              style={{ display: "flex", flexDirection: "column", gap: "14px" }}
            >
              <p style={{ fontSize: "13px", color: "var(--muted-foreground)", margin: 0 }}>
                Help us understand what’s wrong with this listing. If reporting an image, our AI safety system will automatically review it.
              </p>

              <div className="rm-field">
                <label htmlFor="report-reason" className="rm-label">
                  Reason <span className="rm-required">(required)</span>
                </label>
                <select
                  id="report-reason"
                  className="rm-input"
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value as ReportReason)}
                  required
                >
                  <option value="EXPLICIT_IMAGE">Explicit or inappropriate image</option>
                  <option value="IMAGE_MISMATCH">Image does not match description</option>
                  <option value="AUTHENTICITY_SUSPICION">Suspicion of counterfeit / fake item</option>
                  <option value="SCAM_OR_MISLEADING">Scam or misleading listing</option>
                  <option value="SPAM">Spam or duplicate listing</option>
                  <option value="OTHER">Other concern</option>
                </select>
              </div>

              <div className="rm-field">
                <label htmlFor="report-desc" className="rm-label">
                  Additional details (optional)
                </label>
                <textarea
                  id="report-desc"
                  className="rm-input"
                  rows={3}
                  maxLength={1000}
                  placeholder="Tell us what you noticed…"
                  value={reportDescription}
                  onChange={(e) => setReportDescription(e.target.value)}
                />
              </div>

              {reportError && (
                <p className="form-error" role="alert" style={{ fontSize: "13px" }}>
                  {reportError}
                </p>
              )}

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
                <Button variant="secondary" type="button" onClick={() => setReportOpen(false)}>
                  Cancel
                </Button>
                <Button variant="destructive" type="submit" disabled={reportSubmitting}>
                  {reportSubmitting ? "Submitting…" : "Submit report"}
                </Button>
              </div>
            </form>
          )}
        </Dialog>
      )}
    </article>}
  </Dialog>;
}
