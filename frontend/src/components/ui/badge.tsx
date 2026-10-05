import type { ComponentProps } from "react";

export type BadgeTone = "neutral" | "offer" | "request" | "success" | "warning" | "destructive";
export function Badge({ tone = "neutral", className = "", ...props }: ComponentProps<"span"> & { tone?: BadgeTone }) {
  return <span {...props} className={`rm-badge rm-badge--${tone} ${className}`} />;
}

const statuses = {
  DRAFT: { label: "Draft", tone: "neutral" },
  PENDING_REVIEW: { label: "Pending review", tone: "warning" },
  PUBLISHED: { label: "Published", tone: "success" },
  REJECTED: { label: "Rejected", tone: "destructive" },
  ARCHIVED: { label: "Archived", tone: "neutral" },
  SOLD: { label: "Sold", tone: "neutral" },
  RENTED: { label: "Rented", tone: "neutral" },
  CLOSED: { label: "Closed", tone: "neutral" },
} as const;

export type PostStatus = keyof typeof statuses;

/** Presentation only; does not determine lifecycle transitions or permissions. */
export function StatusBadge({ status, ...props }: Omit<ComponentProps<"span">, "children"> & { status: PostStatus }) {
  const { label, tone } = statuses[status];
  return <Badge {...props} tone={tone}>{label}</Badge>;
}
