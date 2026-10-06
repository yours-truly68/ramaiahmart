import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://ramaiahmart.com";

  return {
    rules: [
      {
        userAgent: "*",
        allow: [
          "/",
          "/login",
          "/register",
          "/forgot-password",
          "/privacy",
          "/terms",
          "/og-image.png",
          "/opengraph-image",
          "/twitter-image",
          "/images/",
          "/fonts/",
        ],
        disallow: [
          "/messages",
          "/messages/",
          "/profile",
          "/profile/",
          "/post/create",
          "/post/create/",
          "/design-system",
          "/design-system/",
          "/api/",
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
