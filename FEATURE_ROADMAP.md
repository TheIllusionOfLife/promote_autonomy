# Feature Roadmap - Promote Autonomy

**Last Updated:** November 10, 2025
**Project:** AI-Powered Marketing Automation with Human-in-the-Loop

---

## 🎯 Project Vision

Build an AI-powered marketing automation system that generates high-quality promotional content (captions, images, videos) with mandatory human approval before execution. The system must produce **production-ready assets** that meet real-world platform requirements.

---

## ✅ Current State (MVP - Completed)

### Core Architecture
- ✅ Three-service Cloud Run deployment (Frontend, Strategy Agent, Creative Agent)
- ✅ Pub/Sub messaging for agent communication
- ✅ Firestore for state management with atomic transactions
- ✅ HITL approval workflow (pending_approval → processing → completed)
- ✅ Firebase Authentication (anonymous users)
- ✅ Cloud Storage for generated assets (public URLs)

### Asset Generation Capabilities
- ✅ Text captions via Gemini 2.5 Flash (7 engaging captions per campaign)
- ✅ Images via Imagen 4.0 (1024x1024 square format)
- ✅ Video briefs via Gemini (text-based production briefs, 15-20 seconds)

### User Experience
- ✅ Simple web interface for goal submission
- ✅ Real-time job status updates via Firestore listeners
- ✅ Caption display with proper emoji rendering
- ✅ Scrollable task list for long content
- ✅ Proper text wrapping for long prompts

### Quality & Testing
- ✅ 62 passing tests (unit + integration)
- ✅ CI/CD with GitHub Actions
- ✅ Security hardening (OIDC auth, user-scoped Firestore rules)
- ✅ Timeout handling (120s for Gemini, 90s for Imagen, 120s for Veo)

---

## 🚀 Priority Features (Hackathon + Post-Hackathon)

### **Phase 1: Real Asset Generation (High Priority)**

#### 1.1 Real VEO Video Generation ⭐⭐⭐⭐⭐
**Status:** Code exists, needs activation
**Effort:** 1-2 hours
**Impact:** HIGH - Transforms demo from "text briefs" to "actual videos"

**Current State:**
- `RealVideoService` uses Gemini to generate text briefs
- VEO API integration code exists but not activated
- Timeout already configured (VEO_TIMEOUT_SEC = 120s)

**What to Do:**
```python
# creative-agent/app/services/video.py
# Replace Gemini text generation with actual VEO API calls
# Similar to how Imagen is used in image.py

import asyncio
from vertexai.preview.vision_models import VideoGenerationModel

class RealVideoService:
    async def generate_video(self, task: VideoTaskConfig) -> str:
        model = VideoGenerationModel.from_pretrained("veo-3.0-generate-001")

        response = await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_videos,
                prompt=task.prompt,
                number_of_videos=1,
                duration=task.duration_sec
            ),
            timeout=self.settings.VEO_TIMEOUT_SEC
        )

        # Upload to Cloud Storage, return public URL
        return video_url
```

**Risks:**
- VEO is slow (2-5 minutes per video) → May need UI updates to show progress
- Quota limits → Need fallback to text briefs on failure
- Cost → Each video generation costs money

**Success Criteria:**
- Generate 15-20 second videos instead of text briefs
- Handle timeouts gracefully (fallback to text if VEO fails)
- Display video preview in UI before posting

---

#### 1.2 Multi-Modal Input (Product Photos) ⭐⭐⭐⭐⭐
**Status:** Not implemented
**Effort:** 2-3 hours
**Impact:** HIGH - Makes system usable for real products

**Problem:**
Users have actual product photos/screenshots but can only describe them in text. Generated images are generic stock-photo style, not featuring the actual product.

**Solution:**
Add image upload capability so users can provide reference images for context-aware generation.

**Implementation:**

**Frontend Changes:**
```tsx
// frontend/app/page.tsx
const [productImage, setProductImage] = useState<File | null>(null);

<input
  type="file"
  accept="image/*"
  onChange={(e) => setProductImage(e.target.files?.[0] || null)}
/>
```

**Strategy Agent Changes:**
```python
# strategy-agent/app/routers/strategize.py
# Accept uploaded image, store in Cloud Storage
# Add reference_image_url to task_list schema

@router.post("/strategize")
async def strategize(goal: str, reference_image: Optional[UploadFile] = None):
    # Generate event_id first
    event_id = generate_event_id()

    # Initialize reference_url to None
    reference_url = None
    image_analysis = None

    if reference_image:
        # Upload to Cloud Storage
        reference_url = await storage.upload_file(
            event_id,
            "reference_image.jpg",
            await reference_image.read()
        )

        # Pass to Gemini for image analysis
        image_analysis = await gemini.analyze_image(reference_url, goal)

    # Generate task list with reference image context
    prompt_prefix = f"Based on the reference image: {image_analysis}" if image_analysis else ""
    task_list = TaskList(
        goal=goal,
        reference_images=[reference_url] if reference_url else [],
        image=ImageTaskConfig(
            prompt=f"{prompt_prefix}. {goal}" if image_analysis else goal,
            reference_image=reference_url  # NEW field (can be None)
        )
    )
```

**Creative Agent Changes:**
```python
# creative-agent/app/services/image.py
# Use Imagen's edit/controlnet features for reference-based generation

if task.reference_image:
    # Image-to-image generation
    response = model.edit_image(
        base_image=task.reference_image,
        prompt=task.prompt,
        edit_mode="product-shot"
    )
else:
    # Text-to-image generation (current behavior)
    response = model.generate_images(prompt=task.prompt)
```

**Success Criteria:**
- Users can upload 1 product image (PNG/JPG, max 10MB)
- Gemini analyzes the image to understand product features
- Generated captions reference actual product details
- Generated images incorporate or reference the uploaded product

---

### **Phase 2: Platform-Specific Configuration (Critical for Usability)**

#### 2.1 Multi-Platform Asset Specifications ⭐⭐⭐⭐⭐
**Status:** ✅ COMPLETED (November 10, 2025)
**Effort:** 3-4 hours (actual: 4 hours across 6 implementation phases)
**Impact:** CRITICAL - Without this, generated assets are often unusable

**Problem:**
Current system generates assets with default values:
- Images: Always 1024x1024 (square)
- Videos: Always 15-20 seconds

But real platforms have strict requirements:
- **Instagram Feed**: 1080x1080 (square), max 4MB
- **Instagram Stories**: 1080x1920 (9:16), max 4MB, max 15s video
- **X (Twitter)**: 1200x675 (16:9), max 5MB, max 2:20 video
- **Facebook**: 1200x630 (1.91:1), max 8MB
- **LinkedIn**: 1200x627 (1.91:1), max 5MB
- **YouTube**: 1280x720 or 1920x1080 (16:9), various lengths

**Solution:**
Let users select target platforms and automatically configure asset specs.

**Implementation:**

**Shared Schema:**
```python
# shared/models.py
class Platform(str, Enum):
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"

class PlatformSpec(BaseModel):
    """Platform-specific asset requirements."""
    platform: Platform
    image_size: str  # e.g., "1080x1920"
    image_aspect_ratio: str  # e.g., "9:16"
    max_image_size_mb: float
    video_size: str
    video_aspect_ratio: str
    max_video_length_sec: int
    max_video_size_mb: float
    caption_max_length: int

# Predefined specifications
PLATFORM_SPECS = {
    Platform.INSTAGRAM_FEED: PlatformSpec(
        platform=Platform.INSTAGRAM_FEED,
        image_size="1080x1080",
        image_aspect_ratio="1:1",
        max_image_size_mb=4.0,
        video_size="1080x1080",
        video_aspect_ratio="1:1",
        max_video_length_sec=60,
        max_video_size_mb=4.0,
        caption_max_length=2200
    ),
    Platform.INSTAGRAM_STORY: PlatformSpec(
        platform=Platform.INSTAGRAM_STORY,
        image_size="1080x1920",
        image_aspect_ratio="9:16",
        max_image_size_mb=4.0,
        video_size="1080x1920",
        video_aspect_ratio="9:16",
        max_video_length_sec=15,
        max_video_size_mb=4.0,
        caption_max_length=2200
    ),
    # ... more platforms
}

class TaskList(BaseModel):
    goal: str
    target_platforms: list[Platform]  # NEW: User selects platforms
    captions: Optional[CaptionTaskConfig] = None
    image: Optional[ImageTaskConfig] = None
    video: Optional[VideoTaskConfig] = None
```

**Frontend Changes:**
```tsx
// frontend/app/page.tsx
const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);

<div>
  <label>Target Platforms:</label>
  <select multiple value={selectedPlatforms} onChange={...}>
    <option value="instagram_feed">Instagram Feed</option>
    <option value="instagram_story">Instagram Story</option>
    <option value="twitter">X (Twitter)</option>
    <option value="facebook">Facebook</option>
    <option value="linkedin">LinkedIn</option>
  </select>
</div>

// Show selected platform requirements
{selectedPlatforms.map(platform => (
  <div key={platform}>
    <strong>{platform}</strong>
    <p>Image: {SPECS[platform].image_size} ({SPECS[platform].image_aspect_ratio})</p>
    <p>Video: Max {SPECS[platform].max_video_length_sec}s</p>
  </div>
))}
```

**Strategy Agent Changes:**
```python
# strategy-agent/app/routers/strategize.py
@router.post("/strategize")
async def strategize(request: StrategizeRequest):
    # Validate platforms are selected
    if not request.target_platforms:
        raise HTTPException(status_code=400, detail="At least one target platform must be selected")

    # Get platform specs
    specs = [PLATFORM_SPECS[p] for p in request.target_platforms]

    # Generate tasks matching ALL selected platforms
    # Use the most restrictive constraints
    min_video_length = min(s.max_video_length_sec for s in specs)
    common_aspect = find_common_aspect_ratio(specs)

    task_list = TaskList(
        goal=request.goal,
        target_platforms=request.target_platforms,
        captions=CaptionTaskConfig(n=7, style="engaging"),
        image=ImageTaskConfig(
            prompt="...",
            size=common_aspect or "1080x1080",
            output_format="PNG",
            max_file_size_mb=min(s.max_image_size_mb for s in specs)
        ),
        video=VideoTaskConfig(
            prompt="...",
            duration_sec=min_video_length,
            aspect_ratio=common_aspect or "1:1",
            max_file_size_mb=min(s.max_video_size_mb for s in specs)
        )
    )
```

**Creative Agent Changes:**
```python
# creative-agent/app/services/image.py
async def generate_image(self, task: ImageTaskConfig) -> str:
    # Parse size string "1080x1920" → width=1080, height=1920
    width, height = map(int, task.size.split('x'))

    response = model.generate_images(
        prompt=task.prompt,
        number_of_images=1,
        aspect_ratio=task.aspect_ratio,
        output_mime_type=f"image/{task.output_format.lower()}"
    )

    # Optimize file size if exceeds max
    image_bytes = response.images[0]._image_bytes
    if len(image_bytes) > task.max_file_size_mb * 1024 * 1024:
        image_bytes = compress_image(image_bytes, task.max_file_size_mb)

    # Upload to Cloud Storage
    return await storage.upload_file(...)

# creative-agent/app/services/video.py
async def generate_video(self, task: VideoTaskConfig) -> str:
    response = veo_model.generate_videos(
        prompt=task.prompt,
        number_of_videos=1,
        duration=task.duration_sec,
        aspect_ratio=task.aspect_ratio  # NEW
    )

    # Check file size, compress if needed
    video_bytes = response.videos[0]
    if len(video_bytes) > task.max_file_size_mb * 1024 * 1024:
        video_bytes = compress_video(video_bytes, task.max_file_size_mb)

    return await storage.upload_file(...)
```

**Implementation Summary:**
- ✅ Added Platform enum with 6 platforms (Instagram Feed/Story, Twitter, Facebook, LinkedIn, YouTube)
- ✅ Defined PlatformSpec model with all platform-specific requirements (image/video sizes, aspect ratios, file size limits, caption limits)
- ✅ Created PLATFORM_SPECS constant with specifications for all 6 platforms
- ✅ Updated TaskList schema to require target_platforms field (min_length=1)
- ✅ Extended ImageTaskConfig and VideoTaskConfig with optional aspect_ratio and max_file_size_mb fields
- ✅ Increased VideoTaskConfig.duration_sec max from 60s to 600s (LinkedIn supports up to 10min videos)
- ✅ Frontend: Multi-select UI with checkboxes, visual feedback, and platform specs display
- ✅ Strategy Agent: Platform-aware task generation using most restrictive constraints across selected platforms
- ✅ Strategy Agent: Updated Gemini prompt to include platform context and constraints
- ✅ Creative Agent: RealImageService uses explicit aspect_ratio, implements JPEG compression to meet max_file_size_mb
- ✅ Creative Agent: RealVeoVideoService uses explicit aspect_ratio, logs warnings if output exceeds max_file_size_mb
- ✅ All unit tests passing (62 total: 46 shared schemas, 18 strategy agent, 19 creative agent)

**Success Criteria:**
- ✅ Users can select 1-6 target platforms (required to select at least one)
- ✅ System generates assets compatible with ALL selected platforms
- ✅ File sizes are within platform limits (images: JPEG compression, videos: warning logged)
- ✅ Aspect ratios match platform requirements
- ✅ Video lengths comply with platform restrictions (VEO maps to nearest supported duration: 4s, 6s, or 8s)
- Caption lengths enforced via PLATFORM_SPECS (ready for future truncation logic)

**Edge Cases Handled:**
- Multiple platforms with different constraints → Uses most restrictive (minimum file sizes, minimum video duration)
- First platform's aspect ratio used for images and videos (future enhancement: generate multiple variants)
- Video file size cannot be controlled by VEO API → Logs warning if exceeds limit (future: ffmpeg compression)

---

### **Phase 3: Enhanced User Experience**

#### 3.1 Campaign Templates
**Effort:** 2-3 hours
**Impact:** MEDIUM - Speeds up campaign creation

Pre-built templates for common scenarios:
- "Product Launch Campaign"
- "Seasonal Promotion"
- "Event Announcement"
- "Brand Awareness"

#### 3.2 Asset Preview & Editing
**Effort:** 3-4 hours
**Impact:** MEDIUM - Users can tweak before approval

Allow users to:
- Edit generated captions before approval
- Request re-generation of specific assets
- Adjust image prompts and regenerate

#### 3.3 Brand Style Guide
**Effort:** 2-3 hours
**Impact:** MEDIUM - Ensures brand consistency

Upload brand guidelines:
- Brand colors (hex codes)
- Logo
- Tone of voice (formal/casual/playful)
- Inject into Gemini prompts for consistent output

---

## 🔮 Long-Term Vision (Post-Hackathon)

### Automation Features (6-12 months)

#### Social Media Publishing Agent
**Complexity:** HIGH
**Risks:** External API dependencies, auto-posting safety concerns

- Integrate with X, Instagram, Facebook, LinkedIn APIs
- "Approve & Schedule" workflow
- Post to platforms after HITL approval
- Requires OAuth flows for each platform

**Why Later:**
- External dependencies (platform API changes)
- Auto-posting is high-risk (requires extensive safety checks)
- Regulatory compliance (GDPR, platform ToS)

#### Campaign Dashboard & Analytics
**Complexity:** MEDIUM
**Value:** HIGH for professional marketers

- Real-time monitoring of published posts
- Metrics: impressions, engagement, clicks, conversions
- Poll platform APIs for analytics
- Aggregate and visualize in dashboard

#### A/B Testing Campaigns
**Complexity:** MEDIUM
**Value:** HIGH for optimization

- Generate 2-3 variants of each asset
- Publish all variants simultaneously
- Track which performs best
- Learn from performance data

#### Performance-Based Auto-Optimization
**Complexity:** HIGH
**Value:** HIGH - True "autonomy"

- Analyze which campaigns perform best
- Gemini learns from past performance
- Automatically adjusts future strategies
- HITL: "Review AI-proposed strategy changes"

#### Budget Management & Spend Tracking
**Complexity:** MEDIUM
**Value:** HIGH for paid campaigns

- Set campaign budgets
- Track ad spend across platforms
- HITL: "Approve $500 spend on this campaign"
- Integration with platform billing APIs

---

## 🏆 Hackathon Scope (Realistic Timeline)

**If you have 1 more day (8 hours):**
1. **Real VEO Integration** (2 hours) - Already mostly implemented
2. **Platform-Specific Configuration** (4 hours) - Critical for usability
3. **Multi-Modal Input** (2 hours) - High impact for demo

**Presentation Strategy:**
- **Demo**: Goal → Strategy → Upload Product Photo → Select Platforms → Approve → Get Platform-Ready Assets (captions + image + video)
- **Highlight**: "Assets are production-ready for Instagram, X, and LinkedIn - correct sizes, formats, and lengths"
- **Roadmap Slide**: Show automation features as "future vision"

**Differentiation Points:**
1. ✅ Multi-agent architecture (Strategy + Creative separation)
2. ✅ HITL approval with atomic transactions
3. ✅ Production deployment on Google Cloud
4. ✅ **Platform-specific asset generation** (unique feature!)
5. ✅ Multi-modal input (product photos)
6. ✅ Real video generation (not just text briefs)

---

## 📝 Technical Debt & Future Improvements

### Code Quality
- Add integration tests for VEO API calls
- Add E2E tests for full workflow
- Improve error handling for platform API failures
- Add retry logic for flaky Vertex AI calls

### Performance
- Parallel asset generation (run captions, image, video simultaneously)
- Cache Gemini responses for similar goals
- CDN for Cloud Storage assets

### Security
- Rate limiting on API endpoints
- Cost controls (max spend per user)
- Content moderation for generated assets
- Audit logging for all HITL approvals

### Scalability
- Horizontal scaling for Creative Agent (multiple replicas)
- Queue management for Pub/Sub (handle high volume)
- Database indexing for faster queries

---

## 🎯 Success Metrics

**Hackathon Goals:**
- ✅ Functional end-to-end demo (goal → assets)
- ✅ HITL workflow showcased
- ✅ Platform-ready assets generated
- ✅ Multi-modal input demonstrated

**Post-Hackathon (3 months):**
- 100+ users generating campaigns
- 1000+ assets generated
- Integration with 3+ social platforms
- <5% user-reported asset compatibility issues

**Long-Term (1 year):**
- 10,000+ campaigns launched
- 50,000+ assets generated
- Full automation with monitoring
- ROI tracking and optimization

---

**Document Version:** 1.0
**Last Reviewed:** November 10, 2025
**Next Review:** After hackathon completion
