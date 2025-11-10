/**
 * TypeScript types matching the shared Python schemas.
 */

export type JobStatus =
  | 'pending_approval'
  | 'processing'
  | 'completed'
  | 'rejected'
  | 'failed';

export type Platform =
  | 'instagram_feed'
  | 'instagram_story'
  | 'twitter'
  | 'facebook'
  | 'linkedin'
  | 'youtube';

export interface PlatformSpec {
  platform: Platform;
  image_size: string;
  image_aspect_ratio: string;
  max_image_size_mb: number;
  video_size: string;
  video_aspect_ratio: string;
  max_video_length_sec: number;
  max_video_size_mb: number;
  caption_max_length: number;
}

export const PLATFORM_SPECS: Record<Platform, PlatformSpec> = {
  instagram_feed: {
    platform: 'instagram_feed',
    image_size: '1080x1080',
    image_aspect_ratio: '1:1',
    max_image_size_mb: 4.0,
    video_size: '1080x1080',
    video_aspect_ratio: '1:1',
    max_video_length_sec: 60,
    max_video_size_mb: 4.0,
    caption_max_length: 2200,
  },
  instagram_story: {
    platform: 'instagram_story',
    image_size: '1080x1920',
    image_aspect_ratio: '9:16',
    max_image_size_mb: 4.0,
    video_size: '1080x1920',
    video_aspect_ratio: '9:16',
    max_video_length_sec: 15,
    max_video_size_mb: 4.0,
    caption_max_length: 2200,
  },
  twitter: {
    platform: 'twitter',
    image_size: '1200x675',
    image_aspect_ratio: '16:9',
    max_image_size_mb: 5.0,
    video_size: '1280x720',
    video_aspect_ratio: '16:9',
    max_video_length_sec: 140,
    max_video_size_mb: 512.0,
    caption_max_length: 280,
  },
  facebook: {
    platform: 'facebook',
    image_size: '1200x630',
    image_aspect_ratio: '1.91:1',
    max_image_size_mb: 8.0,
    video_size: '1280x720',
    video_aspect_ratio: '16:9',
    max_video_length_sec: 240,
    max_video_size_mb: 4096.0,
    caption_max_length: 63206,
  },
  linkedin: {
    platform: 'linkedin',
    image_size: '1200x627',
    image_aspect_ratio: '1.91:1',
    max_image_size_mb: 5.0,
    video_size: '1280x720',
    video_aspect_ratio: '16:9',
    max_video_length_sec: 600,
    max_video_size_mb: 5120.0,
    caption_max_length: 3000,
  },
  youtube: {
    platform: 'youtube',
    image_size: '1280x720',
    image_aspect_ratio: '16:9',
    max_image_size_mb: 2.0,
    video_size: '1920x1080',
    video_aspect_ratio: '16:9',
    max_video_length_sec: 60,
    max_video_size_mb: 256.0,
    caption_max_length: 5000,
  },
};

export interface CaptionTaskConfig {
  n: number;
  style: string;
}

export interface ImageTaskConfig {
  prompt: string;
  size: string;
  aspect_ratio?: string;
  max_file_size_mb?: number;
}

export interface VideoTaskConfig {
  prompt: string;
  duration_sec: number;
  aspect_ratio?: string;
  max_file_size_mb?: number;
}

export interface TaskList {
  goal: string;
  target_platforms: Platform[];
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
  target_platforms: Platform[];
  uid: string;
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
