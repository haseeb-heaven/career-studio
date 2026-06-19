export interface ContactLink {
  id?: number;
  label: string;
  url: string;
}

export interface Skill {
  id?: number;
  name: string;
  category: string;
  years: number;
}

export interface ExperienceBullet {
  id?: number;
  text: string;
}

export interface Experience {
  id?: number;
  company: string;
  role: string;
  start: string;
  end: string;
  location: string;
  bullets: ExperienceBullet[];
}

export interface Project {
  id?: number;
  name: string;
  description: string;
  link: string;
  tech: string[];
}

export interface Education {
  id?: number;
  institution: string;
  degree: string;
  field: string;
  start: string;
  end: string;
}

export interface Certification {
  id?: number;
  cert_id?: string;
  name: string;
  issuer: string;
  date: string;
}

export interface Profile {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  availability: string;
  compensation: string;
  links: ContactLink[];
  skills: Skill[];
  experience: Experience[];
  projects: Project[];
  education: Education[];
  certifications: Certification[];
}

export interface ImportResult {
  profile_id: number;
  warnings: string[];
}

export interface AuthUser {
  user_id: number;
  username: string;
  token: string;
}
