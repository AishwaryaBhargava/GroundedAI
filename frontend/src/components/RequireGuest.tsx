import { Navigate } from "react-router-dom";

export default function RequireGuest({ children }: { children: JSX.Element }) {
  const sessionId = localStorage.getItem("guest_session_id");

  if (!sessionId) {
    return <Navigate to="/" replace />;
  }

  return children;
}
