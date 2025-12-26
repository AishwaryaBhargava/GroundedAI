import { apiFetch } from "./api";

export type Workspace = {
  id: string;
  name: string;
  is_guest: boolean;
  created_at?: string;
};

export async function listWorkspaces(): Promise<Workspace[]> {
  return apiFetch<Workspace[]>("/workspaces", { method: "GET" });
}

export async function createWorkspace(name: string): Promise<Workspace> {
  return apiFetch<Workspace>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}
