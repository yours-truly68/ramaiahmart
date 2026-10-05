import { LoaderCircle } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

export type ButtonProps = ComponentProps<"button"> & {
  variant?: "primary" | "accent" | "secondary" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export function Button({ variant = "primary", size = "md", loading = false, disabled, type = "button", className = "", children, ...props }: ButtonProps) {
  return (
    <button {...props} type={type} className={`rm-button rm-button--${variant} rm-button--${size} ${className}`} disabled={disabled || loading} aria-busy={loading || undefined}>
      {loading && <LoaderCircle className="rm-spinner" size={18} aria-hidden="true" />}
      {children}
    </button>
  );
}

type IconButtonProps = Omit<ButtonProps, "children" | "aria-label"> & {
  "aria-label": string;
  children: ReactNode;
};

export function IconButton({ className = "", variant = "ghost", children, loading, ...props }: IconButtonProps) {
  return <Button {...props} loading={loading} variant={variant} className={`rm-icon-button ${className}`}>{!loading && <span aria-hidden="true">{children}</span>}</Button>;
}
