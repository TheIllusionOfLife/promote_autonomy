/**
 * API client for Strategy Agent endpoints.
 */

import { auth } from './firebase';
import type { StrategizeRequest, StrategizeResponse, ApproveRequest, ApproveResponse } from './types';

const STRATEGY_AGENT_URL = process.env.NEXT_PUBLIC_STRATEGY_AGENT_URL || 'http://localhost:8000';

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
export async function strategize(request: StrategizeRequest): Promise<StrategizeResponse> {
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
      ...request,
      uid: user.uid,
    }),
  });

  if (!response.ok) {
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Strategize failed: ${response.statusText}`);
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
      throw new Error(errorData.detail || `Approve failed: ${response.statusText}`);
    } else {
      const error = await response.text();
      throw new Error(`Approve failed: ${error || response.statusText}`);
    }
  }

  return await response.json();
}
