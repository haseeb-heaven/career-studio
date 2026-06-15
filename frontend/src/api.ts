import axios from "axios";
import type { Profile, ImportResult, AuthUser } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000/api";

// ---- Auth token management ----
export function setAuthToken(token: string | null): void {
  if (token) {
    axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete axios.defaults.headers.common["Authorization"];
  }
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
}

export async function register(username: string, password: string, email = ""): Promise<TokenOut> {
  const res = await axios.post<TokenOut>(`${BASE}/auth/register`, { username, password, email });
  return res.data;
}

export async function login(username: string, password: string): Promise<TokenOut> {
  const form = new FormData();
  form.append("username", username);
  form.append("password", password);
  const res = await axios.post<TokenOut>(`${BASE}/auth/login`, form);
  return res.data;
}

export async function verifyToken(): Promise<AuthUser | null> {
  try {
    const res = await axios.get<{ user_id: number; username: string; email: string }>(`${BASE}/auth/me`);
    const token = (axios.defaults.headers.common["Authorization"] as string)?.replace("Bearer ", "") ?? "";
    return { user_id: res.data.user_id, username: res.data.username, token };
  } catch {
    return null;
  }
}

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

// ---- Section CRUD ----
import type { Skill, Experience, Project, Education, Certification } from "./types";

// Skills
export async function addSkill(profileId: number, data: Omit<Skill, "id">): Promise<Skill> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/skills`, data);
  return res.data;
}
export async function updateSkill(profileId: number, skillId: number, data: Partial<Skill>): Promise<Skill> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/skills/${skillId}`, data);
  return res.data;
}
export async function deleteSkill(profileId: number, skillId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/skills/${skillId}`);
}

// Experience
export async function addExperience(profileId: number, data: Omit<Experience, "id">): Promise<Experience> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/experience`, data);
  return res.data;
}
export async function updateExperience(profileId: number, expId: number, data: Partial<Experience>): Promise<Experience> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/experience/${expId}`, data);
  return res.data;
}
export async function deleteExperience(profileId: number, expId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/experience/${expId}`);
}

// Bullets
export async function addBullet(profileId: number, expId: number, text: string): Promise<{ id: number; text: string }> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/experience/${expId}/bullets`, { text });
  return res.data;
}
export async function updateBullet(profileId: number, expId: number, bulletId: number, text: string): Promise<{ id: number; text: string }> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/experience/${expId}/bullets/${bulletId}`, { text });
  return res.data;
}
export async function deleteBullet(profileId: number, expId: number, bulletId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/experience/${expId}/bullets/${bulletId}`);
}

// Projects
export async function addProject(profileId: number, data: Omit<Project, "id">): Promise<Project> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/projects`, data);
  return res.data;
}
export async function updateProject(profileId: number, projId: number, data: Partial<Project>): Promise<Project> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/projects/${projId}`, data);
  return res.data;
}
export async function deleteProject(profileId: number, projId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/projects/${projId}`);
}

// Education
export async function addEducation(profileId: number, data: Omit<Education, "id">): Promise<Education> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/education`, data);
  return res.data;
}
export async function updateEducation(profileId: number, eduId: number, data: Partial<Education>): Promise<Education> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/education/${eduId}`, data);
  return res.data;
}
export async function deleteEducation(profileId: number, eduId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/education/${eduId}`);
}

// Certifications
export async function addCertification(profileId: number, data: Omit<Certification, "id">): Promise<Certification> {
  const res = await axios.post(`${BASE}/profiles/${profileId}/certifications`, data);
  return res.data;
}
export async function updateCertification(profileId: number, certId: number, data: Partial<Certification>): Promise<Certification> {
  const res = await axios.patch(`${BASE}/profiles/${profileId}/certifications/${certId}`, data);
  return res.data;
}
export async function deleteCertification(profileId: number, certId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/certifications/${certId}`);
}
