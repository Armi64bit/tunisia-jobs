"use client";

import { CheckIcon, EmergencyIcon } from "./icons";

interface ToastProps {
  message: string | null;
  kind: "ok" | "err";
}

export default function Toast({ message, kind }: ToastProps) {
  const cls = `toast show toast--${kind}`;
  return (
    <div className={cls} role="status" aria-live="polite">
      {kind === "err" ? <EmergencyIcon /> : <CheckIcon />}
      <span>{message}</span>
    </div>
  );
}