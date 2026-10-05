"use client";

import Image from "next/image";
import { useState } from "react";

/** Use decorative when the person's name is already rendered beside the avatar. */
export function Avatar({ name, src, size = "md", decorative = false, className = "" }: { name: string; src?: string; size?: "sm" | "md" | "lg"; decorative?: boolean; className?: string }) {
  const [failedSource, setFailedSource] = useState<string>();
  const initials = name.trim().split(/\s+/).slice(0, 2).map(part => Array.from(part)[0]).join("").toLocaleUpperCase() || "?";
  const showImage = src && src !== failedSource;
  return <span className={`rm-avatar rm-avatar--${size} ${className}`} role={decorative ? undefined : "img"} aria-label={decorative ? undefined : name} aria-hidden={decorative || undefined}>{showImage ? <Image src={src} alt="" width={96} height={96} unoptimized onError={() => setFailedSource(src)} /> : <span aria-hidden="true">{initials}</span>}</span>;
}
