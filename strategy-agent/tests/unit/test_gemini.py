"""Tests for Gemini service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.gemini import MockGeminiService, RealGeminiService
from promote_autonomy_shared.schemas import Platform


class TestMockGeminiService:
    """Tests for MockGeminiService."""

    @pytest.mark.asyncio
    async def test_analyze_reference_image(self):
        """Test analyzing reference image with mock service."""
        service = MockGeminiService()

        analysis = await service.analyze_reference_image(
            "https://storage.googleapis.com/bucket/product.jpg",
            "Promote new sneakers"
        )

        # Mock should return a formatted analysis
        assert isinstance(analysis, str)
        assert len(analysis) >= 50  # Should be substantial
        assert "product" in analysis.lower() or "image" in analysis.lower()

    @pytest.mark.asyncio
    async def test_analyze_reference_image_includes_goal_context(self):
        """Test that analysis includes goal context."""
        service = MockGeminiService()

        analysis = await service.analyze_reference_image(
            "https://storage.googleapis.com/bucket/laptop.jpg",
            "Launch new laptop model"
        )

        assert isinstance(analysis, str)
        assert "laptop" in analysis.lower() or "tech" in analysis.lower() or "product" in analysis.lower()

    @pytest.mark.asyncio
    async def test_generate_task_list_with_reference_analysis(self):
        """Test generating task list with reference image analysis."""
        service = MockGeminiService()

        task_list = await service.generate_task_list(
            goal="Promote eco-friendly water bottle",
            target_platforms=[Platform.INSTAGRAM_FEED],
            reference_analysis="Product image shows: sleek stainless steel water bottle in forest green color, minimalist design with bamboo cap, outdoor hiking scene background. Brand elements: eco-friendly messaging, nature photography style, warm earth tones."
        )

        # Task list should be influenced by the analysis
        assert task_list.goal == "Promote eco-friendly water bottle"
        assert Platform.INSTAGRAM_FEED in task_list.target_platforms

        # Image prompt should incorporate analysis context
        if task_list.image:
            prompt = task_list.image.prompt.lower()
            # Should reference product details from analysis
            assert any(word in prompt for word in ["eco", "bottle", "green", "nature", "outdoor"])


class TestRealGeminiService:
    """Tests for RealGeminiService."""

    @pytest.mark.asyncio
    async def test_analyze_reference_image(self):
        """Test analyzing reference image with real service."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel") as mock_model_class:

            # Setup mocks
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = """
Product Analysis:
- Product Type: Running shoes
- Brand Elements: Nike swoosh logo prominently displayed
- Colors: Bold red and white color scheme
- Composition: Product shot on clean white background, professional studio lighting
- Mood: Energetic and athletic, conveying performance and speed
- Key Features: Visible air cushioning technology, mesh upper for breathability
- Visual Style: Clean, modern product photography with high contrast
            """.strip()

            mock_model.generate_content = Mock(return_value=mock_response)
            mock_model_class.return_value = mock_model

            service = RealGeminiService()

            analysis = await service.analyze_reference_image(
                "https://storage.googleapis.com/bucket/shoes.jpg",
                "Launch new running shoes"
            )

            # Verify generate_content was called
            assert mock_model.generate_content.called
            call_args = mock_model.generate_content.call_args[0][0]

            # call_args is a list [image_part, prompt]
            assert isinstance(call_args, list)
            assert len(call_args) == 2

            # Verify prompt (second element) includes goal and analysis request
            prompt = call_args[1]
            assert "running shoes" in prompt.lower() or "launch" in prompt.lower()

            # Verify analysis returned
            assert isinstance(analysis, str)
            assert len(analysis) > 100  # Should be detailed
            assert "Product" in analysis or "running shoes" in analysis.lower()

    @pytest.mark.asyncio
    async def test_analyze_reference_image_detailed_prompt(self):
        """Test that analysis uses detailed prompt for marketing purposes."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel") as mock_model_class:

            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = "Detailed product analysis with brand elements, composition, and mood."

            mock_model.generate_content = Mock(return_value=mock_response)
            mock_model_class.return_value = mock_model

            service = RealGeminiService()

            await service.analyze_reference_image(
                "https://storage.googleapis.com/bucket/product.jpg",
                "Promote new product"
            )

            call_args = mock_model.generate_content.call_args[0][0]

            # call_args is a list [image_part, prompt]
            prompt = call_args[1]

            # Verify prompt asks for detailed marketing analysis
            assert any(keyword in prompt.lower() for keyword in [
                "brand elements", "composition", "mood", "visual style", "marketing"
            ])

    @pytest.mark.asyncio
    async def test_generate_task_list_with_reference_analysis(self):
        """Test generating task list with reference analysis context."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel") as mock_model_class:

            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = """
{
  "goal": "Promote artisan coffee beans",
  "target_platforms": ["instagram_feed"],
  "captions": {"n": 5, "style": "engaging"},
  "image": {
    "prompt": "Artisan coffee beans in rustic burlap sack, warm brown tones, cozy cafe aesthetic matching reference image",
    "size": "1080x1080",
    "aspect_ratio": "1:1",
    "max_file_size_mb": 4.0
  }
}
            """.strip()

            mock_model.generate_content = Mock(return_value=mock_response)
            mock_model_class.return_value = mock_model

            service = RealGeminiService()

            task_list = await service.generate_task_list(
                goal="Promote artisan coffee beans",
                target_platforms=[Platform.INSTAGRAM_FEED],
                reference_analysis="Product image shows premium coffee beans in rustic burlap sack, warm brown tones, natural wood background, cozy cafe aesthetic"
            )

            # Verify generate_content was called with reference analysis in prompt
            call_args = mock_model.generate_content.call_args[0][0]
            assert "reference" in call_args.lower() or "product image" in call_args.lower()
            assert "coffee" in call_args.lower() or "burlap" in call_args.lower()

            # Verify task list generated correctly
            assert task_list.goal == "Promote artisan coffee beans"
            assert task_list.image is not None
            assert "coffee" in task_list.image.prompt.lower() or "rustic" in task_list.image.prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_reference_image_with_timeout(self):
        """Test that analysis handles timeout gracefully with fallback."""
        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel") as mock_model_class, \
             patch("app.services.gemini.asyncio.wait_for") as mock_wait_for:

            mock_model = Mock()
            mock_model_class.return_value = mock_model

            # Mock wait_for to raise timeout
            mock_wait_for.side_effect = asyncio.TimeoutError()

            service = RealGeminiService()

            # Should not raise, but return fallback analysis
            analysis = await service.analyze_reference_image(
                "https://storage.googleapis.com/bucket/image.jpg",
                "Test goal"
            )

            # Verify timeout was used
            assert mock_wait_for.called

            # Verify fallback analysis was returned
            assert isinstance(analysis, str)
            assert "Reference product image" in analysis or "test goal" in analysis.lower()


import asyncio
