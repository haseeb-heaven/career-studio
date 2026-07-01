import axios from "axios";
import type { Profile, ImportResult, AuthUser } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8001/api";

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

export async function forgotPassword(username: string): Promise<{ message: string; dev_reset_url?: string | null }> {
  const res = await axios.post<{ message: string; dev_reset_url?: string | null }>(`${BASE}/auth/forgot-password`, { username });
  return res.data;
}

export async function resetPassword(token: string, new_password: string): Promise<{ message: string }> {
  const res = await axios.post<{ message: string }>(`${BASE}/auth/reset-password`, { token, new_password });
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

export async function exportProfileBlob(profileId: number, fmt: string): Promise<Blob> {
  const res = await axios.get(`${BASE}/profiles/${profileId}/export/${fmt}`, {
    responseType: "blob",
  });
  return res.data;
}


// ---- Settings ----
export async function getSettings(): Promise<Record<string, string>> {
  const res = await axios.get(`${BASE}/settings`);
  return res.data;
}

export async function updateSettings(data: Record<string, string>): Promise<void> {
  await axios.put(`${BASE}/settings`, data);
}

export async function testApiKey(provider: string, apiKey: string): Promise<{ ok: boolean; message: string }> {
  const res = await axios.post(`${BASE}/settings/test-key`, { provider, api_key: apiKey });
  return res.data;
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

// ---- Resume Editor ----
export interface ResumeDraft {
  id: number;
  title: string;
  content: string;
  created_at?: string;
  updated_at?: string;
}

export async function generateResumeDraft(profileId: number, title?: string): Promise<ResumeDraft> {
  const res = await axios.post<ResumeDraft>(`${BASE}/profiles/${profileId}/resume-drafts/generate`, {
    title: title ?? "",
  });
  return res.data;
}

export async function listResumeDrafts(profileId: number): Promise<ResumeDraft[]> {
  const res = await axios.get<ResumeDraft[]>(`${BASE}/profiles/${profileId}/resume-drafts`);
  return res.data;
}

export async function saveResumeDraft(
  profileId: number,
  draftId: number,
  content: string,
  title?: string
): Promise<ResumeDraft> {
  const res = await axios.put<ResumeDraft>(`${BASE}/profiles/${profileId}/resume-drafts/${draftId}`, {
    content,
    title,
  });
  return res.data;
}

export async function deleteResumeDraft(profileId: number, draftId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/resume-drafts/${draftId}`);
}

export async function suggestResumeEdits(profileId: number, draftId: number): Promise<string[]> {
  const res = await axios.post<{ suggestions: string[] }>(
    `${BASE}/profiles/${profileId}/resume-drafts/${draftId}/suggest`
  );
  return res.data.suggestions;
}

export async function exportResumeDraftBlob(profileId: number, draftId: number, fmt: string): Promise<Blob> {
  const res = await axios.get(`${BASE}/profiles/${profileId}/resume-drafts/${draftId}/export/${fmt}`, {
    responseType: "blob",
  });
  return res.data;
}

// ---- Jobs ----
export interface SkillDetail {
  skill: string;
  status: "matched" | "partial" | "missing" | "extra";
  confidence: number;
  severity: "required" | "nice_to_have";
  category?: string;
  via?: string;
}

export interface GapEntry {
  status: "ok" | "weak" | "gap";
  message: string;
  items?: string[];
}

export interface Gaps {
  skills?: GapEntry;
  experience?: GapEntry;
  location?: GapEntry;
  seniority?: GapEntry;
  education?: GapEntry;
  certifications?: GapEntry;
}

export interface JobMatch {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  source: string;
  match_score: number;
  salary?: string | null;
  is_deep_link: boolean;
  date_posted?: string;
  job_type?: string;
  industry?: string;
  is_remote?: boolean;
  is_expired?: boolean;
  salary_min?: number;
  salary_max?: number;
  match_breakdown?: Record<string, number>;
  matched_skills?: string[];
  missing_skills?: string[];
  skill_details?: SkillDetail[];
  gaps?: Gaps;
  hire_chance?: number;
  hire_chance_label?: string;
  insight?: string;
  confidence?: string;
}

export interface JobsSearchResult {
  query: string;
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
  jobs: JobMatch[];
}

export interface JobSearchOptions {
  limit?: number;
  offset?: number;
  jobTitle?: string;
  location?: string;
  portal?: string;
  minYears?: number;
  maxYears?: number;
  datePosted?: "any" | "last_24h" | "last_7d" | "last_30d";
  minMatchScore?: number;
  jobType?: string;
  minSalary?: number;
  maxSalary?: number;
  industries?: string;
  sort?: "best_match" | "recent" | "salary" | "location";
}

export interface SavedFilter {
  id: number;
  name: string;
  filters: Record<string, string | number>;
  sort: string;
  created_at: string;
}

export interface ExternalSearchLink {
  portal: string;
  label: string;
  url: string;
  icon: string;
}

export async function searchJobs(
  profileId: number,
  options: JobSearchOptions | number = {},
  jobTitle = "",
  location = "",
  portal = "all",
): Promise<JobsSearchResult> {
  // Backwards-compatible overload: searchJobs(pid, limit, jobTitle, location, portal)
  let opts: JobSearchOptions;
  if (typeof options === "number") {
    opts = { limit: options, jobTitle, location, portal };
  } else {
    opts = options;
  }
  const params = new URLSearchParams();
  if (opts.limit !== undefined) params.append("limit", String(opts.limit));
  if (opts.offset !== undefined) params.append("offset", String(opts.offset));
  if (opts.jobTitle) params.append("job_title", opts.jobTitle);
  if (opts.location) params.append("location", opts.location);
  if (opts.portal) params.append("portal", opts.portal);
  if (opts.minYears !== undefined && opts.minYears > 0) params.append("min_years", String(opts.minYears));
  if (opts.maxYears !== undefined && opts.maxYears < 50) params.append("max_years", String(opts.maxYears));
  if (opts.datePosted && opts.datePosted !== "any") params.append("date_posted", opts.datePosted);
  if (opts.minMatchScore !== undefined && opts.minMatchScore > 0) params.append("min_match_score", String(opts.minMatchScore));
  if (opts.jobType) params.append("job_type", opts.jobType);
  if (opts.minSalary !== undefined && opts.minSalary > 0) params.append("min_salary", String(opts.minSalary));
  if (opts.maxSalary !== undefined && opts.maxSalary > 0) params.append("max_salary", String(opts.maxSalary));
  if (opts.industries) params.append("industries", opts.industries);
  if (opts.sort) params.append("sort", opts.sort);
  const res = await axios.get<JobsSearchResult>(`${BASE}/profiles/${profileId}/jobs?${params.toString()}`);
  return res.data;
}

export async function listSavedFilters(profileId: number): Promise<SavedFilter[]> {
  const res = await axios.get<SavedFilter[]>(`${BASE}/profiles/${profileId}/saved-filters`);
  return res.data;
}

export async function createSavedFilter(
  profileId: number,
  name: string,
  filters: Record<string, string | number>,
  sort = "best_match",
): Promise<SavedFilter> {
  const res = await axios.post<SavedFilter>(
    `${BASE}/profiles/${profileId}/saved-filters`,
    { name, filters, sort },
  );
  return res.data;
}

export async function deleteSavedFilter(profileId: number, sfId: number): Promise<void> {
  await axios.delete(`${BASE}/profiles/${profileId}/saved-filters/${sfId}`);
}

export async function updateSavedFilter(
  profileId: number,
  sfId: number,
  body: { name?: string; filters?: Record<string, string | number>; sort?: string },
): Promise<SavedFilter> {
  const res = await axios.patch<SavedFilter>(
    `${BASE}/profiles/${profileId}/saved-filters/${sfId}`,
    body,
  );
  return res.data;
}

export async function getExternalSearchLinks(
  profileId: number,
  keywords = "",
  location = "",
  experienceLevel = "",
  workType = "",
  timePosted = "",
  salaryMin = 0,
  salaryCurrency = "USD",
): Promise<{ keywords: string; location: string; currency: string; links: ExternalSearchLink[] }> {
  const params = new URLSearchParams();
  if (keywords) params.append("keywords", keywords);
  if (location) params.append("location", location);
  if (experienceLevel) params.append("experience_level", experienceLevel);
  if (workType) params.append("work_type", workType);
  if (timePosted) params.append("time_posted", timePosted);
  if (salaryMin > 0) params.append("salary_min", String(salaryMin));
  if (salaryCurrency) params.append("salary_currency", salaryCurrency);
  const qs = params.toString();
  const res = await axios.get(
    `${BASE}/profiles/${profileId}/external-search${qs ? `?${qs}` : ""}`,
  );
  return res.data;
}

// ---- Resume Keywords (advanced matching) ----

export interface ResumeKeyword {
  term: string;
  canonical: string;
  weight: number;
  source: string;
  confidence: number;
}

export interface ResumeKeywordsResult {
  keywords: ResumeKeyword[];
  total: number;
  top_terms: string[];
}

export async function fetchResumeKeywords(
  profileId: number,
): Promise<ResumeKeywordsResult> {
  const res = await axios.get<ResumeKeywordsResult>(
    `${BASE}/profiles/${profileId}/resume-keywords`,
  );
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
