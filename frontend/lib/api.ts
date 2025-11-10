/**
 * API client for Strategy Agent endpoints.
 */

import { auth } from './firebase';
import type { StrategizeRequest, StrategizeResponse, ApproveRequest, ApproveResponse } from './types';

const STRATEGY_AGENT_URL = process.env.NEXT_PUBLIC_STRATEGY_AGENT_URL || 'http://localhost:8000';

/**
 * Format FastAPI validation error details into a readable message.
 */
function formatErrorDetail(detail: unknown): string {
  // If detail is a string, return it directly
  if (typeof detail === 'string') {
    return detail;
  }

  // If detail is an array of validation errors (FastAPI 422 format)
  if (Array.isArray(detail)) {
    return detail
      .map((err: { loc?: (string | number)[]; msg?: string }) => {
        const field = err.loc?.slice(1).join('.') || 'field';
        const message = err.msg || 'validation error';
        return `${field}: ${message}`;
      })
      .join(', ');
  }

  // Fallback for other types
  return JSON.stringify(detail);
}

/**
 * Get current user's ID token for API authentication.
 */
async function getIdToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }
  return await user.getIdToken();
}

/**
 * Call Strategy Agent to generate a marketing strategy.
 */
export async function strategize(goal: string, target_platforms: string[]): Promise<StrategizeResponse> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }

  const idToken = await getIdToken();

  const response = await fetch(`${STRATEGY_AGENT_URL}/api/strategize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${idToken}`,
    },
    body: JSON.stringify({
      goal,
      target_platforms,
      uid: user.uid,
    } as StrategizeRequest),
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const errorData = await response.json();
      const errorMessage = errorData.detail
        ? formatErrorDetail(errorData.detail)
        : `Strategize failed: ${response.statusText}`;
      throw new Error(errorMessage);
    } else {
      const error = await response.text();
      throw new Error(`Strategize failed: ${error || response.statusText}`);
    }
  }

  return await response.json();
}

/**
 * Approve a pending strategy and trigger asset generation.
 */
export async function approveJob(eventId: string): Promise<ApproveResponse> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }

  const idToken = await getIdToken();

  const response = await fetch(`${STRATEGY_AGENT_URL}/api/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${idToken}`,
    },
    body: JSON.stringify({
      event_id: eventId,
      uid: user.uid,
    } as ApproveRequest),
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const errorData = await response.json();
      const errorMessage = errorData.detail
        ? formatErrorDetail(errorData.detail)
        : `Approve failed: ${response.statusText}`;
      throw new Error(errorMessage);
    } else {
      const error = await response.text();
      throw new Error(`Approve failed: ${error || response.statusText}`);
    }
  }

  return await response.json();
}
