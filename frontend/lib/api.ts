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
export async function strategize(goal: string): Promise<StrategizeResponse> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }

  const response = await fetch(`${STRATEGY_AGENT_URL}/api/strategize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      goal,
      uid: user.uid,
    } as StrategizeRequest),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Strategize failed: ${error}`);
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
    const error = await response.text();
    throw new Error(`Approve failed: ${error}`);
  }

  return await response.json();
}
