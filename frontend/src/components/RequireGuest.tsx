import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

export default function RequireGuest({ children }: { children: ReactNode }) {
  const sessionId = localStorage.getItem("guest_session_id");

  if (!sessionId) {
    return <Navigate to="/" replace />;
  }

  return children;
}
