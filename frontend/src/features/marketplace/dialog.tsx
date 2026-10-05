"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const previousOverflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    return () => { dialog.close(); document.body.style.overflow = previousOverflow; };
  }, []);
  return <dialog ref={ref} className="market-dialog" aria-labelledby={id} onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="dialog-inner"><header className="dialog-header"><h2 id={id}>{title}</h2><button className="plain-icon" aria-label="Close panel" onClick={onClose}><X size={22} /></button></header>{children}</div>
  </dialog>;
}
