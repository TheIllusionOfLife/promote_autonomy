'use client';

import { useState, useEffect } from 'react';
import { onAuthStateChanged, signInAnonymously, User } from 'firebase/auth';
import { doc, onSnapshot } from 'firebase/firestore';
import { auth, db } from '@/lib/firebase';
import { strategize, approveJob } from '@/lib/api';
import type { Job, BrandStyle, Platform } from '@/lib/types';
import { PLATFORM_SPECS } from '@/lib/types';
import BrandStyleForm from '@/components/BrandStyleForm';

function detectAspectRatioConflicts(platforms: Platform[]): string[] {
  if (platforms.length <= 1) return [];

  // Use PLATFORM_SPECS to avoid hardcoding aspect ratios (DRY)
  const getAspectRatio = (p: Platform) => PLATFORM_SPECS[p].image_aspect_ratio;

  const portrait = platforms.filter(p => getAspectRatio(p) === '9:16');
  const square = platforms.filter(p => getAspectRatio(p) === '1:1');
  const landscape = platforms.filter(p => ['16:9', '1.91:1'].includes(getAspectRatio(p)));

  const categoriesUsed = [portrait, square, landscape].filter(c => c.length > 0).length;

  if (categoriesUsed > 1) {
    const firstPlatform = platforms[0];
    const firstRatio = getAspectRatio(firstPlatform);
    const conflicting = platforms.slice(1)
      .filter(p => getAspectRatio(p) !== firstRatio)
      .map(p => `${p.replace('_', ' ')} (${getAspectRatio(p)})`);

    if (conflicting.length > 0) {
      return [`⚠️ Selected platforms have different aspect ratios. Assets will use ${firstPlatform.replace('_', ' ')} format (${firstRatio}). Conflicting: ${conflicting.join(', ')}`];
    }
  }

  return [];
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [goal, setGoal] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([]);
  const [referenceImage, setReferenceImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const [actualCaptions, setActualCaptions] = useState<string[]>([]);
  const [useBrandStyle, setUseBrandStyle] = useState(false);
  const [brandStyle, setBrandStyle] = useState<BrandStyle | null>(null);
  const [clientWarnings, setClientWarnings] = useState<string[]>([]);
  const [strategizeWarnings, setStrategizeWarnings] = useState<string[]>([]);

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

  // Detect aspect ratio conflicts when platforms change
  useEffect(() => {
    const warnings = detectAspectRatioConflicts(selectedPlatforms);
    setClientWarnings(warnings);
  }, [selectedPlatforms]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('Please upload a JPEG or PNG image');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image must be less than 10MB');
      return;
    }

    setReferenceImage(file);
    setError('');

    // Generate preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setReferenceImage(null);
    setImagePreview(null);
  };

  const handleStrategize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || !user || selectedPlatforms.length === 0) return;

    setLoading(true);
    setError('');

    try {
      const response = await strategize({
        goal,
        target_platforms: selectedPlatforms,
        uid: user.uid,
        brand_style: useBrandStyle && brandStyle ? brandStyle : undefined,
        referenceImage: referenceImage,
      });

      // Store backend warnings from strategy response
      setStrategizeWarnings(response.warnings || []);

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
      setStrategizeWarnings([]); // Clear stale warnings on error
    } finally {
      setLoading(false);
    }
  };

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const platformLabels: Record<Platform, string> = {
    instagram_feed: 'Instagram Feed',
    instagram_story: 'Instagram Story',
    twitter: 'X (Twitter)',
    facebook: 'Facebook',
    linkedin: 'LinkedIn',
    youtube: 'YouTube',
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

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 'bold' }}>
              Target Platforms (select at least one):
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
              {(Object.keys(platformLabels) as Platform[]).map(platform => (
                <label
                  key={platform}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0.75rem',
                    border: `2px solid ${selectedPlatforms.includes(platform) ? '#0070f3' : '#ddd'}`,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    background: selectedPlatforms.includes(platform) ? '#e6f2ff' : 'white',
                    transition: 'all 0.2s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedPlatforms.includes(platform)}
                    onChange={() => togglePlatform(platform)}
                    disabled={loading}
                    style={{ marginRight: '0.5rem', cursor: 'pointer' }}
                  />
                  <span>{platformLabels[platform]}</span>
                </label>
              ))}
            </div>

            {selectedPlatforms.length > 0 && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                background: '#f5f5f5',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}>
                <strong>Selected Platforms ({selectedPlatforms.length}):</strong>
                <div style={{ marginTop: '0.5rem' }}>
                  {selectedPlatforms.map(platform => {
                    const spec = PLATFORM_SPECS[platform];
                    return (
                      <div key={platform} style={{ marginBottom: '0.5rem', paddingLeft: '1rem' }}>
                        <strong>{platformLabels[platform]}:</strong>{' '}
                        Image {spec.image_aspect_ratio} ({spec.image_size}),
                        Video {spec.video_aspect_ratio} (max {spec.max_video_length_sec}s),
                        Captions max {spec.caption_max_length} chars
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Client-side aspect ratio warnings */}
          {clientWarnings.length > 0 && (
            <div style={{
              background: '#fffbeb',
              borderLeft: '4px solid #f59e0b',
              padding: '1rem',
              marginBottom: '1rem',
              borderRadius: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '1.25rem', marginRight: '0.75rem' }}>⚠️</span>
                <div style={{ flex: 1 }}>
                  {clientWarnings.map((warning, idx) => (
                    <p key={idx} style={{ margin: 0, color: '#92400e', fontSize: '0.9rem' }}>
                      {warning}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}

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

          {/* Reference Image Upload */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.75rem', fontWeight: 'bold' }}>
              Product Image (Optional):
            </label>
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
              Upload a product photo to generate visually consistent marketing materials
            </p>

            {!imagePreview ? (
              <div>
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  onChange={handleImageUpload}
                  disabled={loading}
                  style={{ display: 'none' }}
                  id="reference-image-input"
                />
                <label
                  htmlFor="reference-image-input"
                  style={{
                    display: 'inline-block',
                    padding: '0.75rem 1.5rem',
                    background: '#f5f5f5',
                    border: '2px dashed #ddd',
                    borderRadius: '6px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  📷 Choose Image (PNG/JPG, max 10MB)
                </label>
              </div>
            ) : (
              <div style={{
                border: '2px solid #ddd',
                borderRadius: '6px',
                padding: '1rem',
                background: '#f9f9f9'
              }}>
                <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>
                    {referenceImage?.name}
                  </span>
                  <button
                    type="button"
                    onClick={handleRemoveImage}
                    disabled={loading}
                    style={{
                      padding: '0.25rem 0.75rem',
                      background: '#ff4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      fontSize: '0.85rem'
                    }}
                  >
                    Remove
                  </button>
                </div>
                <img
                  src={imagePreview}
                  alt="Reference product"
                  style={{
                    maxWidth: '100%',
                    maxHeight: '300px',
                    borderRadius: '4px',
                    display: 'block'
                  }}
                />
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !goal.trim() || selectedPlatforms.length === 0}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              background: (loading || !goal.trim() || selectedPlatforms.length === 0) ? '#ccc' : '#0070f3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: (loading || !goal.trim() || selectedPlatforms.length === 0) ? 'not-allowed' : 'pointer',
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

            <p style={{ marginBottom: '1rem' }}>
              <strong>Target Platforms:</strong>{' '}
              {currentJob.task_list.target_platforms.map(p => platformLabels[p]).join(', ')}
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

            {/* Backend strategy warnings */}
            {strategizeWarnings.length > 0 && (
              <div style={{
                background: '#fffbeb',
                borderLeft: '4px solid #f59e0b',
                padding: '1rem',
                marginTop: '1rem',
                marginBottom: '1rem',
                borderRadius: '4px'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '1.25rem', marginRight: '0.75rem' }}>⚠️</span>
                  <div style={{ flex: 1 }}>
                    <strong style={{ color: '#92400e', display: 'block', marginBottom: '0.5rem' }}>
                      Strategy Warnings
                    </strong>
                    {strategizeWarnings.map((warning, idx) => (
                      <p key={idx} style={{ margin: '0.25rem 0', color: '#92400e', fontSize: '0.9rem' }}>
                        {warning}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
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
                {/* Job warnings from asset generation */}
                {currentJob.warnings && currentJob.warnings.length > 0 && (
                  <div style={{
                    background: '#fffbeb',
                    borderLeft: '4px solid #f59e0b',
                    padding: '1rem',
                    marginBottom: '1.5rem',
                    borderRadius: '4px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                      <span style={{ fontSize: '1.25rem', marginRight: '0.75rem' }}>⚠️</span>
                      <div style={{ flex: 1 }}>
                        <strong style={{ color: '#92400e', display: 'block', marginBottom: '0.5rem' }}>
                          Asset Generation Warnings ({currentJob.warnings.length})
                        </strong>
                        {currentJob.warnings.map((warning, idx) => (
                          <p key={idx} style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '0.9rem' }}>
                            • {warning}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

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
