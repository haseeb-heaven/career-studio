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

// ---- Settings ----
export async function getSettings(): Promise<Record<string, string>> {
  const res = await axios.get(`${BASE}/settings`);
  return res.data;
}

export async function updateSettings(data: Record<string, string>): Promise<void> {
  await axios.put(`${BASE}/settings`, data);
}

// ---- Logs ----
export interface ActivityLog {
  id: number;
  action: string;
  detail: string;
  profile_id: number | null;
  created_at: string;
}

export async function getLogs(limit = 200): Promise<ActivityLog[]> {
  const res = await axios.get(`${BASE}/logs?limit=${limit}`);
  return res.data;
}

export async function clearLogs(): Promise<void> {
  await axios.delete(`${BASE}/logs`);
}

export async function getLogStats(): Promise<{ total: number; by_action: Record<string, number> }> {
  const res = await axios.get(`${BASE}/logs/stats`);
  return res.data;
}

// ---- Analysis ----
export interface AnalysisResult {
  score: number;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  ats_keywords: string[];
}

export async function analyzeProfile(profileId: number): Promise<AnalysisResult> {
  const res = await axios.post<AnalysisResult>(`${BASE}/profiles/${profileId}/analyze`);
  return res.data;
}

// ---- Cover Letter ----
export interface CoverLetterResult {
  id: number;
  job_title: string;
  company: string;
  content: string;
  created_at?: string;
}

export async function generateCoverLetter(
  profileId: number,
  job_title: string,
  company: string,
  extra_notes?: string
): Promise<CoverLetterResult> {
  const res = await axios.post<CoverLetterResult>(`${BASE}/profiles/${profileId}/cover-letter`, {
    job_title,
    company,
    extra_notes: extra_notes ?? "",
  });
  return res.data;
}

export async function listCoverLetters(profileId: number): Promise<CoverLetterResult[]> {
  const res = await axios.get<CoverLetterResult[]>(`${BASE}/profiles/${profileId}/cover-letters`);
  return res.data;
}

export async function deleteCoverLetter(profileId: number, clId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/cover-letters/${clId}`);
}

// ---- Roadmap ----
export interface RoadmapResult {
  id: number;
  plan_type: string;
  content: string;
  created_at?: string;
}

export async function generateRoadmap(
  profileId: number,
  plan_type: string,
  target_role: string,
  years_horizon: number
): Promise<RoadmapResult> {
  const res = await axios.post<RoadmapResult>(`${BASE}/profiles/${profileId}/roadmap`, {
    plan_type,
    target_role,
    years_horizon,
  });
  return res.data;
}

export async function listRoadmaps(profileId: number): Promise<RoadmapResult[]> {
  const res = await axios.get<RoadmapResult[]>(`${BASE}/profiles/${profileId}/roadmaps`);
  return res.data;
}

export async function deleteRoadmap(profileId: number, planId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/roadmaps/${planId}`);
}

// ---- Jobs ----
export interface JobMatch {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  source: string;
  match_score: number;
}

export async function searchJobs(profileId: number, limit = 20): Promise<{ query: string; jobs: JobMatch[] }> {
  const res = await axios.get(`${BASE}/profiles/${profileId}/jobs?limit=${limit}`);
  return res.data;
}
