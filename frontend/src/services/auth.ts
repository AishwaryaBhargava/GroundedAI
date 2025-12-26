import { apiFetch } from "./api";

type GuestSessionResponse = {
  session_id: string;
  created_at?: string;
};

export async function createGuestSession(): Promise<GuestSessionResponse> {
  return apiFetch<GuestSessionResponse>("/auth/guest", {
    method: "POST",
  });
}
