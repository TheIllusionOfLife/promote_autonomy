'use client';

import { useState, useEffect } from 'react';
import { onAuthStateChanged, signInAnonymously, User } from 'firebase/auth';
import { doc, onSnapshot } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';
import { strategize, approveJob } from '@/lib/api';
import type { Job, BrandStyle } from '@/lib/types';
import BrandStyleForm from '@/components/BrandStyleForm';

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const [actualCaptions, setActualCaptions] = useState<string[]>([]);
  const [useBrandStyle, setUseBrandStyle] = useState(false);
  const [brandStyle, setBrandStyle] = useState<BrandStyle | null>(null);

  // Auto sign-in anonymously
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        setUser(user);
      } else {
        // Sign in anonymously if not authenticated
        try {
          const result = await signInAnonymously(auth);
          setUser(result.user);
        } catch (err) {
          console.error('Auth error:', err);
          setError('Authentication failed. Please refresh the page.');
        }
      }
    });

    return () => unsubscribe();
  }, []);

  // Listen to job updates
  useEffect(() => {
    if (!currentJob?.event_id || !user) return;

    const unsubscribe = onSnapshot(
      doc(db, 'jobs', currentJob.event_id),
      (doc) => {
        if (doc.exists()) {
          setCurrentJob(doc.data() as Job);
        }
      },
      (error) => {
        console.error('Firestore listener error:', error);
      }
    );

    return () => unsubscribe();
  }, [currentJob?.event_id, user]);

  // Fetch actual captions from the URL when job is completed
  useEffect(() => {
    const abortController = new AbortController();

    const fetchCaptions = async () => {
      // Extract caption URL and validate it
      const captionsUrl = currentJob?.captions?.[0]?.trim();

      if (currentJob?.status === 'completed' && captionsUrl) {
        try {
          // Security: Validate URL is from expected Cloud Storage bucket
          const ALLOWED_BUCKET = 'promote-autonomy-assets';
          const url = new URL(captionsUrl);

          if (url.hostname !== 'storage.googleapis.com' ||
              !url.pathname.startsWith(`/${ALLOWED_BUCKET}/`)) {
            throw new Error('Invalid caption URL: must be from Cloud Storage bucket');
          }

          const response = await fetch(captionsUrl, { signal: abortController.signal });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const captionsData = await response.json();

          // Validate response is an array of strings
          if (!Array.isArray(captionsData) || !captionsData.every(item => typeof item === 'string')) {
            throw new Error('Invalid captions data format');
          }

          if (!abortController.signal.aborted) {
            setActualCaptions(captionsData);
          }
        } catch (err) {
          if (!abortController.signal.aborted) {
            console.error('Failed to fetch captions:', err);
            setActualCaptions([]);
            setError('Failed to load captions. Please try again.');
          }
        }
      } else {
        setActualCaptions([]);
      }
    };

    fetchCaptions();

    return () => {
      abortController.abort();
    };
  }, [currentJob?.status, currentJob?.captions?.[0]]);

  const handleStrategize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || !user) return;

    setLoading(true);
    setError('');

    try {
      const response = await strategize({
        goal,
        uid: user.uid,
        brand_style: useBrandStyle && brandStyle ? brandStyle : undefined,
      });
      // The job will be populated via Firestore listener
      setCurrentJob({
        event_id: response.event_id,
        uid: user.uid,
        status: response.status,
        task_list: response.task_list,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        captions: [],
        images: [],
        videos: [],
        audit_logs: [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate strategy');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!currentJob) return;

    setLoading(true);
    setError('');

    try {
      await approveJob(currentJob.event_id);
      // Job status will update via Firestore listener
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem' }}>
      <h1 style={{ marginBottom: '2rem' }}>Promote Autonomy</h1>

      {!currentJob ? (
        <form onSubmit={handleStrategize} style={{ marginBottom: '2rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="goal" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Marketing Goal:
            </label>
            <input
              id="goal"
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g., Launch awareness campaign for new AI product"
              style={{
                width: '100%',
                padding: '0.5rem',
                fontSize: '1rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
              disabled={loading}
            />
          </div>

          {/* Brand Style Guide Toggle */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useBrandStyle}
                onChange={(e) => {
                  setUseBrandStyle(e.target.checked);
                  if (!e.target.checked) {
                    setBrandStyle(null);
                  } else if (!brandStyle) {
                    // Initialize with default brand style
                    setBrandStyle({
                      colors: [{ hex_code: '000000', name: 'Primary', usage: 'primary' }],
                      tone: 'professional',
                    });
                  }
                }}
                disabled={loading}
              />
              <span style={{ fontWeight: 500 }}>Use Brand Style Guide</span>
            </label>
          </div>

          {/* Brand Style Form */}
          {useBrandStyle && (
            <div style={{ marginBottom: '1.5rem' }}>
              <BrandStyleForm value={brandStyle} onChange={setBrandStyle} />
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !goal.trim()}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              background: '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Generating...' : 'Generate Strategy'}
          </button>
        </form>
      ) : (
        <div>
          <h2>Job Status: {currentJob.status}</h2>
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            marginTop: '1rem',
            maxHeight: '70vh',
            overflowY: 'auto'
          }}>
            <h3>Task List</h3>
            <p style={{ overflowWrap: 'break-word', marginBottom: '1rem' }}>
              <strong>Goal:</strong> {currentJob.task_list.goal}
            </p>

            {currentJob.task_list.captions && (
              <p style={{ marginBottom: '1rem' }}>
                <strong>Captions:</strong> {currentJob.task_list.captions.n} {currentJob.task_list.captions.style} captions
              </p>
            )}

            {currentJob.task_list.image && (
              <p style={{ overflowWrap: 'break-word', marginBottom: '1rem' }}>
                <strong>Image:</strong> {currentJob.task_list.image.size} - {currentJob.task_list.image.prompt}
              </p>
            )}

            {currentJob.task_list.video && (
              <p style={{ overflowWrap: 'break-word', marginBottom: '1rem' }}>
                <strong>Video:</strong> {currentJob.task_list.video.duration_sec}s - {currentJob.task_list.video.prompt}
              </p>
            )}

            {currentJob.status === 'pending_approval' && (
              <button
                onClick={handleApprove}
                disabled={loading}
                style={{
                  marginTop: '1rem',
                  padding: '0.75rem 1.5rem',
                  fontSize: '1rem',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                {loading ? 'Approving...' : 'Approve'}
              </button>
            )}

            {currentJob.status === 'completed' && (
              <div style={{ marginTop: '1rem' }}>
                <h4>Generated Assets:</h4>

                {actualCaptions.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Captions ({actualCaptions.length}):</strong>
                    <ul style={{ marginTop: '0.5rem', listStylePosition: 'inside' }}>
                      {actualCaptions.map((caption, i) => (
                        <li key={i} style={{ marginBottom: '0.5rem', wordWrap: 'break-word' }}>{caption}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {currentJob.images.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Images ({currentJob.images.length}):</strong>
                    <div style={{ marginTop: '0.5rem' }}>
                      {currentJob.images.map((url, i) => (
                        <div key={i} style={{ marginBottom: '0.5rem' }}>
                          <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>
                            View Image {i + 1}
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {currentJob.videos.length > 0 && (
                  <div>
                    <strong>Videos ({currentJob.videos.length}):</strong>
                    <div style={{ marginTop: '0.5rem' }}>
                      {currentJob.videos.map((url, i) => (
                        <div key={i} style={{ marginBottom: '0.5rem' }}>
                          <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>
                            View Video {i + 1}
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={() => setCurrentJob(null)}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            New Job
          </button>
        </div>
      )}

      {error && (
        <div style={{ padding: '1rem', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginTop: '1rem' }}>
          {error}
        </div>
      )}
    </main>
  );
}
