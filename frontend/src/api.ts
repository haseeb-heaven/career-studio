import axios from "axios";
import type { Profile, ImportResult } from "./types";

const BASE = "http://localhost:8000/api";

export async function importFile(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await axios.post<ImportResult>(`${BASE}/import`, form);
  return res.data;
}

export async function listProfiles(): Promise<{ id: number; full_name: string; email: string }[]> {
  const res = await axios.get(`${BASE}/profiles`);
  return res.data;
}

export async function getProfile(id: number): Promise<Profile> {
  const res = await axios.get<Profile>(`${BASE}/profiles/${id}`);
  return res.data;
}

export async function patchProfile(id: number, data: Partial<Profile>): Promise<{ id: number; full_name: string }> {
  const res = await axios.patch(`${BASE}/profiles/${id}`, data);
  return res.data;
}

export async function deleteProfile(id: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${id}`);
}

export function exportUrl(profileId: number, fmt: string): string {
  return `${BASE}/profiles/${profileId}/export/${fmt}`;
}
