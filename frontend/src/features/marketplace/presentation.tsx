"use client";
import { useState } from "react";
import { Bike, BookOpen, Ellipsis, FileText, House, Laptop, Armchair, Shirt, Volleyball, Package, type LucideIcon } from "lucide-react";
import type { Post } from "@/lib/api/types";
import { isSafeHttpUrl } from "@/lib/security/url";

// Presentation hints only. Category identities and names always come from the API.
export const categoryStyles: Record<string, { icon: LucideIcon; tone: string; order: number }> = {
  electronics: { icon: Laptop, tone: "peach", order: 0 },
  books: { icon: BookOpen, tone: "sage", order: 1 },
  furniture: { icon: Armchair, tone: "pink", order: 2 },
  vehicles: { icon: Bike, tone: "blue", order: 3 },
  housing: { icon: House, tone: "yellow", order: 4 },
  notes: { icon: FileText, tone: "lilac", order: 5 },
  fashion: { icon: Shirt, tone: "mint", order: 6 },
  sports: { icon: Volleyball, tone: "peach", order: 7 },
  other: { icon: Ellipsis, tone: "stone", order: 8 },
};
export function categoryStyle(slug: string) { return categoryStyles[slug] ?? { icon: Package, tone: "stone", order: 9 }; }
export function priceLabel(post: Post) {
  if (post.price === null) return "Budget open";
  const amount = Number(post.price);
  if (amount === 0) return post.type === "OFFER" ? "Free" : "Looking to borrow";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount).replace(/\.00$/, "");
}
export function relativeTime(date: string) {
  const seconds = Math.max(0, (Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(date).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
export function ListingImage({ post, detail = false }: { post: Post; detail?: boolean }) {
  const [failed, setFailed] = useState(false);
  const images = post?.images ? [...post.images] : [];
  const image = images.sort((a, b) => a.position - b.position).find(item => item.public_url && isSafeHttpUrl(item.public_url));
  const { icon: Icon, tone } = categoryStyle(post?.category?.slug ?? "");
  return <div className={`listing-photo tone-${tone} ${detail ? "listing-photo--detail" : ""}`}>
    {image && !failed ?
      /* Listing URLs are supplied by the API, including arbitrary S3-compatible hosts. */
      // eslint-disable-next-line @next/next/no-img-element
      <img src={image.public_url!} alt={post.title} loading="lazy" onError={() => setFailed(true)} />
      : <div className="photo-fallback">
          <div className="photo-fallback-icon">
            <Icon size={28} strokeWidth={1.5} aria-hidden="true" />
          </div>
          <span className="photo-fallback-label">{post.type === "REQUEST" ? "Campus Request" : "No photo yet"}</span>
        </div>}
  </div>;
}
