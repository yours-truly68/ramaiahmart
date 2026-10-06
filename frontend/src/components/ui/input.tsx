"use client";

import { Search } from "lucide-react";
import { useId, type ComponentProps, type ReactNode } from "react";

export type InputProps = ComponentProps<"input"> & {
  label: string;
  hint?: ReactNode;
  error?: string;
  leadingIcon?: ReactNode;
};

export function Input({ label, hint, error, leadingIcon, id, className = "", required, "aria-describedby": describedBy, ...props }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const descriptions = [describedBy, hint && hintId, error && errorId].filter(Boolean).join(" ");
  return (
    <div className={`rm-field ${className}`}>
      <label htmlFor={inputId} className="rm-label">{label}{required && <span className="rm-required"> (required)</span>}</label>
      <div className="rm-input-wrap">
        {leadingIcon && <span className="rm-input-icon" aria-hidden="true">{leadingIcon}</span>}
        <input {...props} id={inputId} required={required} aria-invalid={error ? true : props["aria-invalid"]} aria-describedby={descriptions || undefined} className={`rm-input ${leadingIcon ? "rm-input--with-icon" : ""}`} />
      </div>
      {hint && <p className="rm-field-hint" id={hintId}>{hint}</p>}
      {error && <p className="rm-field-error" id={errorId}>{error}</p>}
    </div>
  );
}

export function SearchInput({ label = "Search campus", ...props }: Omit<InputProps, "type" | "leadingIcon" | "label"> & { label?: string }) {
  return <Input {...props} type="search" label={label} leadingIcon={<Search size={20} />} />;
}
