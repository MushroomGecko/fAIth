"""Tests for the APITags enum."""

from enum import Enum

from fAIth.api_tags import APITags


class TestAPITags:
    """Test suite for the APITags enumeration."""

    def test_api_tags_is_enum(self):
        """APITags should be an Enum."""
        assert issubclass(APITags, Enum)

    def test_api_tags_is_string_enum(self):
        """APITags should inherit from str for string equality in Ninja decorators."""
        assert issubclass(APITags, str)

    def test_enum_members_exist(self):
        """APITags should have HEALTH and AI members."""
        assert hasattr(APITags, "HEALTH")
        assert hasattr(APITags, "AI")

    def test_health_tag_value(self):
        """HEALTH tag should have the correct string value."""
        assert APITags.HEALTH == "health"

    def test_ai_tag_value(self):
        """AI tag should have the correct string value."""
        assert APITags.AI == "ai"

    def test_tags_can_be_used_in_list(self):
        """Tags should be usable in lists as Ninja decorator arguments."""
        tags = [APITags.HEALTH, APITags.AI]
        assert len(tags) == 2
        assert APITags.HEALTH in tags
        assert APITags.AI in tags
