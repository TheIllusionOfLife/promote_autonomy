/**
 * TypeScript types matching the shared Python schemas.
 */

export type JobStatus =
  | 'pending_approval'
  | 'processing'
  | 'completed'
  | 'rejected'
  | 'failed';

export interface CaptionTaskConfig {
  n: number;
  style: string;
}

export interface ImageTaskConfig {
  prompt: string;
  size: string;
}

export interface VideoTaskConfig {
  prompt: string;
  duration_sec: number;
}

export type BrandTone =
  | 'professional'
  | 'casual'
  | 'playful'
  | 'luxury'
  | 'technical';

export interface BrandColor {
  hex_code: string;
  name: string;
  usage: 'primary' | 'accent' | 'background' | 'general';
}

export interface BrandStyle {
  colors: BrandColor[];
  tone: BrandTone;
  logo_url?: string;
  tagline?: string;
}

export interface TaskList {
  goal: string;
  brand_style?: BrandStyle;
  captions?: CaptionTaskConfig;
  image?: ImageTaskConfig;
  video?: VideoTaskConfig;
}

export interface Job {
  event_id: string;
  uid: string;
  status: JobStatus;
  task_list: TaskList;
  created_at: string;
  updated_at: string;
  approved_at?: string;
  captions: string[];
  images: string[];
  videos: string[];
  audit_logs: string[];
}

export interface StrategizeRequest {
  goal: string;
  uid: string;
  brand_style?: BrandStyle;
}

export interface StrategizeResponse {
  event_id: string;
  status: JobStatus;
  task_list: TaskList;
}

export interface ApproveRequest {
  event_id: string;
  uid: string;
}

export interface ApproveResponse {
  event_id: string;
  status: JobStatus;
  published: boolean;
  message_id?: string;
}
