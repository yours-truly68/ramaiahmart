import type { ComponentProps, ReactNode } from "react";

export function Card({ surface = "default", elevated = false, className = "", ...props }: ComponentProps<"div"> & { surface?: "default" | "orange" | "sage" | "blue" | "lilac"; elevated?: boolean }) {
  return <div {...props} className={`rm-card rm-card--${surface} ${elevated ? "rm-card--elevated" : ""} ${className}`} />;
}

export function Divider({ className = "", ...props }: ComponentProps<"hr">) {
  return <hr {...props} className={`rm-divider ${className}`} />;
}

export function SectionHeading({ title, description, action, as: Heading = "h2", className = "", ...props }: Omit<ComponentProps<"div">, "title"> & { title: string; description?: string; action?: ReactNode; as?: "h2" | "h3"; }) {
  return <div {...props} className={`rm-section-heading ${className}`}><div><Heading className="rm-heading">{title}</Heading>{description && <p className="rm-muted">{description}</p>}</div>{action && <div className="rm-section-action">{action}</div>}</div>;
}

export function EmptyState({ title, description, icon, action, className = "", ...props }: Omit<ComponentProps<"div">, "title"> & { title: string; description: string; icon?: ReactNode; action?: ReactNode }) {
  return <div {...props} className={`rm-empty-state ${className}`}>{icon && <span className="rm-empty-icon" aria-hidden="true">{icon}</span>}<h3 className="rm-heading-sm">{title}</h3><p className="rm-muted">{description}</p>{action}</div>;
}

/** Decorative placeholder. Label the containing region and mark it aria-busy. */
export function Skeleton({ shape = "line", className = "", style }: { shape?: "line" | "circle" | "image"; className?: string; style?: ComponentProps<"span">["style"] }) {
  return <span aria-hidden="true" style={style} className={`rm-skeleton rm-skeleton--${shape} ${className}`} />;
}
