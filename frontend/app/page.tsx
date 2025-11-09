'use client';

import { useState, useEffect } from 'react';
import { onAuthStateChanged, signInAnonymously, User } from 'firebase/auth';
import { doc, onSnapshot } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';
import { strategize, approveJob } from '@/lib/api';
import type { Job } from '@/lib/types';

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [error, setError] = useState('');

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

  const handleStrategize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || !user) return;

    setLoading(true);
    setError('');

    try {
      const response = await strategize(goal);
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
          <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', marginTop: '1rem' }}>
            <h3>Task List</h3>
            <p><strong>Goal:</strong> {currentJob.task_list.goal}</p>

            {currentJob.task_list.captions && (
              <p><strong>Captions:</strong> {currentJob.task_list.captions.n} {currentJob.task_list.captions.style} captions</p>
            )}

            {currentJob.task_list.image && (
              <p><strong>Image:</strong> {currentJob.task_list.image.size} - {currentJob.task_list.image.prompt}</p>
            )}

            {currentJob.task_list.video && (
              <p><strong>Video:</strong> {currentJob.task_list.video.duration_sec}s - {currentJob.task_list.video.prompt}</p>
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

                {currentJob.captions.length > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <strong>Captions ({currentJob.captions.length}):</strong>
                    <ul style={{ marginTop: '0.5rem' }}>
                      {currentJob.captions.map((caption, i) => (
                        <li key={i} style={{ marginBottom: '0.5rem' }}>{caption}</li>
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
