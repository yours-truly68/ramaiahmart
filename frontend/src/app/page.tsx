import type { Metadata } from "next";
import { Suspense } from "react";
import Home, { FeedSkeleton } from "@/features/marketplace/home";
import type { Post } from "@/lib/api/types";
import { isSafeHttpUrl } from "@/lib/security/url";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

interface PageProps {
  searchParams?: Promise<{ post?: string }>;
}

async function fetchPublicPost(id: string): Promise<Post | null> {
  // Validate UUID format to prevent SSR injection or malformed upstream requests
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    return null;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/posts/${id}`, {
      next: { revalidate: 60 },
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    const post: Post = await res.json();
    if (post.status !== "PUBLISHED") return null;
    return post;
  } catch {
    return null;
  }
}

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  const resolvedParams = searchParams ? await searchParams : undefined;
  const postId = resolvedParams?.post;

  if (!postId) {
    return {
      title: "RamaiahMart — The stuff you need. Already on campus.",
      description:
        "Buy, sell, rent, borrow, and find useful things from fellow Ramaiah students. The campus marketplace for MSRIT.",
      alternates: {
        canonical: "/",
      },
    };
  }

  const post = await fetchPublicPost(postId);
  if (!post) {
    return {
      title: "Marketplace Listing — RamaiahMart",
      description: "Browse student listings, buy, sell, and rent on RamaiahMart.",
      alternates: {
        canonical: "/",
      },
    };
  }

  const title = `${post.title} — RamaiahMart`;
  const cleanDescription = post.description
    ? post.description.replace(/\s+/g, " ").trim().slice(0, 150)
    : `${post.title} available on campus.`;
  const description = `${cleanDescription} View listing and contact the student on RamaiahMart.`;

  const primaryImage = post.images?.find(
    (img) => img.public_url && isSafeHttpUrl(img.public_url)
  )?.public_url;

  return {
    title,
    description,
    alternates: {
      canonical: `/?post=${post.id}`,
    },
    openGraph: {
      title,
      description,
      url: `/?post=${post.id}`,
      type: "article",
      images: primaryImage
        ? [
            {
              url: primaryImage,
              alt: post.title,
            },
          ]
        : [
            {
              url: "/og-image.png",
              width: 1200,
              height: 630,
              alt: "RamaiahMart — Campus Marketplace",
            },
          ],
    },
    twitter: {
      card: primaryImage ? "summary_large_image" : "summary",
      title,
      description,
      images: primaryImage ? [primaryImage] : ["/og-image.png"],
    },
  };
}

export default function Page() {
  return (
    <Suspense
      fallback={
        <main id="main" className="rm-container home-loading">
          <p className="wordmark">
            Ramaiah<span>Mart</span>
          </p>
          <h1>
            The stuff you need.
            <br />
            Already on campus.
          </h1>
          <FeedSkeleton />
        </main>
      }
    >
      <Home />
    </Suspense>
  );
}
