# Cloud Storage Security Model

## Public Access for Marketing Assets

### Current Implementation
All generated marketing assets (captions, images, video briefs) are made **permanently publicly accessible** via Cloud Storage public URLs.

### Rationale
1. **Marketing Content Nature**: Generated assets are promotional materials meant to be shared publicly on social media and marketing channels
2. **Simplicity**: Public URLs can be directly embedded in posts without authentication
3. **Cloud Run Limitations**: Service accounts on Cloud Run don't have private keys needed for signed URL generation

### Requirements
- Bucket must **not** have Public Access Prevention enforced
- Service account needs `storage.objects.setIamPolicy` permission
- All content uploaded to this bucket should be considered public

### Alternative: Signed URLs (Not Currently Used)
Signed URLs provide time-limited access (e.g., 1 hour) and require:
- Service account with private key (not available on Cloud Run by default)
- More complex URL generation
- URLs expire and need regeneration

**Trade-off**: We accept permanent public access because:
- Marketing assets are meant to be public
- No PII or sensitive data in generated content
- Simpler implementation without key management
- Users explicitly approve content before generation

### Security Considerations
- ✅ Users must approve all content before generation (HITL workflow)
- ✅ No user data or PII is generated
- ✅ Assets are stored by event_id (non-guessable ULID)
- ⚠️ No automatic cleanup mechanism (cost consideration)
- ⚠️ Anyone who knows the URL can access the content

### Future Improvements
1. Implement lifecycle policies for automatic cleanup after N days
2. Add manual cleanup command for rejected/outdated content
3. Consider signed URLs if use case changes to include sensitive content
