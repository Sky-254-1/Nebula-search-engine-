"""Tests for hybrid fusion strategies.

Focus areas:
- Linear fusion (weighted sum)
- Reciprocal rank fusion (RRF)
- Interpolation fusion
- Score boundary handling
- Fusion method configuration
"""

from unittest.mock import patch

import pytest

from app.hybrid.fusion import FusionEngine


class TestFusionEngineInitialization:
    """Test FusionEngine initialization."""

    def test_init_default_weights(self):
        """Should initialize with default weights."""
        engine = FusionEngine()

        assert engine.lexical_weight == 0.6
        assert engine.semantic_weight == 0.4
        assert engine.fusion_method == "linear"
        assert engine.rrf_k == 60

    def test_init_custom_weights(self):
        """Should initialize with custom weights."""
        engine = FusionEngine(lexical_weight=0.7, semantic_weight=0.3)

        # Weights should be normalized
        assert engine.lexical_weight == 0.7
        assert engine.semantic_weight == 0.3

    def test_init_normalize_weights(self):
        """Should normalize weights when they don't sum to 1."""
        engine = FusionEngine(lexical_weight=2.0, semantic_weight=2.0)

        assert engine.lexical_weight == 0.5
        assert engine.semantic_weight == 0.5

    def test_init_zero_weights(self):
        """Should handle zero weights."""
        engine = FusionEngine(lexical_weight=0.0, semantic_weight=0.0)

        assert engine.lexical_weight == 0.5
        assert engine.semantic_weight == 0.5

    def test_init_custom_method(self):
        """Should initialize with custom fusion method."""
        engine = FusionEngine(fusion_method="rrf")
        assert engine.fusion_method == "rrf"

    def test_init_invalid_method(self):
        """Should accept any method, validation happens later."""
        engine = FusionEngine(fusion_method="invalid")
        assert engine.fusion_method == "invalid"

    def test_init_custom_rrf_k(self):
        """Should initialize with custom RRF k value."""
        engine = FusionEngine(rrf_k=100)
        assert engine.rrf_k == 100

    def test_supported_methods(self):
        """Should have supported methods list."""
        engine = FusionEngine()

        assert "linear" in engine.supported_methods
        assert "rrf" in engine.supported_methods
        assert "interpolate" in engine.supported_methods


class TestFusionEngineFuse:
    """Test main fuse method."""

    def test_fuse_linear_method(self):
        """Should route to linear fusion."""
        engine = FusionEngine(fusion_method="linear")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["score"] is not None

    def test_fuse_rrf_method(self):
        """Should route to RRF fusion."""
        engine = FusionEngine(fusion_method="rrf")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert "lexical_rrf" in result[0].get("scores", {})

    def test_fuse_interpolate_method(self):
        """Should route to interpolate fusion."""
        engine = FusionEngine(fusion_method="interpolate")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["score"] is not None

    def test_fuse_default_method(self):
        """Should default to linear fusion."""
        engine = FusionEngine()  # No method specified

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1

    def test_fuse_empty_results(self):
        """Should handle empty results."""
        engine = FusionEngine()

        result = engine.fuse([], [], top_k=10)

        assert result == []

    def test_fuse_top_k_limit(self):
        """Should respect top_k limit."""
        engine = FusionEngine()

        lexical = [{"id": str(i), "lexical_score": 0.8} for i in range(20)]
        semantic = [{"id": str(i), "semantic_score": 0.6} for i in range(20)]

        result = engine.fuse(lexical, semantic, top_k=5)

        assert len(result) == 5


class TestLinearFusion:
    """Test linear fusion method."""

    def test_linear_fusion_basic(self):
        """Should calculate weighted sum."""
        engine = FusionEngine(lexical_weight=0.6, semantic_weight=0.4)

        lexical = [{"id": "1", "lexical_score": 1.0}]
        semantic = [{"id": "1", "semantic_score": 0.5}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        # score = 0.6 * 1.0 + 0.4 * 0.5 = 0.8
        assert result[0]["score"] == 0.8

    def test_linear_fusion_multiple_docs(self):
        """Should fuse multiple documents."""
        engine = FusionEngine(lexical_weight=0.5, semantic_weight=0.5)

        lexical = [
            {"id": "1", "lexical_score": 0.8},
            {"id": "2", "lexical_score": 0.6},
            {"id": "3", "lexical_score": 0.4},
        ]
        semantic = [
            {"id": "1", "semantic_score": 0.4},
            {"id": "2", "semantic_score": 0.7},
            {"id": "4", "semantic_score": 0.9},
        ]

        result = engine.fuse(lexical, semantic, top_k=10)

        # Should have 4 unique documents
        assert len(result) == 4

    def test_linear_fusion_scores_normalized(self):
        """Should normalize lexical/semantic scores."""
        engine = FusionEngine(lexical_weight=0.6, semantic_weight=0.4)

        lexical = [{"id": "1", "lexical_score": 1.0}]
        semantic = [{"id": "1", "semantic_score": 0.5}]

        result = engine.fuse(lexical, semantic, top_k=10)

        breakdown = result[0]["score_breakdown"]
        assert breakdown["lexical"]["weight"] == 0.6
        assert breakdown["semantic"]["weight"] == 0.4

    def test_linear_fusion_missing_scores(self):
        """Should handle missing scores."""
        engine = FusionEngine()

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "2"}]  # No semantic_score

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 2

    def test_linear_fusion_score_breakdown(self):
        """Should include score breakdown."""
        engine = FusionEngine(lexical_weight=0.7, semantic_weight=0.3)

        lexical = [{"id": "1", "lexical_score": 1.0}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        breakdown = result[0]["score_breakdown"]
        assert breakdown["fusion_method"] == "linear"
        assert breakdown["lexical"]["raw"] == 1.0
        assert breakdown["semantic"]["raw"] == 0.6


class TestRRFFusion:
    """Test Reciprocal Rank Fusion method."""

    def test_rrf_basic(self):
        """Should calculate RRF score."""
        engine = FusionEngine(fusion_method="rrf", rrf_k=60)

        # Lexical result at rank 1
        lexical = [{"id": "1", "lexical_score": 0.8}]
        # Semantic result at rank 1
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1

        # RRF = 1/(k + rank) for each source, then weighted sum
        # RRF_lexical = 1/(60 + 1) = 1/61 ≈ 0.016
        # RRF_semantic = 1/(60 + 1) = 1/61 ≈ 0.016
        expected_rrf = (1 / 61) * 0.6 + (1 / 61) * 0.4

        assert result[0]["score"] == pytest.approx(expected_rrf, rel=0.01)

    def test_rrf_different_ranks(self):
        """Should handle different ranks."""
        engine = FusionEngine(fusion_method="rrf", rrf_k=60)

        lexical = [
            {"id": "1", "lexical_score": 0.8},  # rank 1
            {"id": "2", "lexical_score": 0.6},  # rank 2
        ]
        semantic = [
            {"id": "1", "semantic_score": 0.6},  # rank 1
            {"id": "3", "semantic_score": 0.4},  # rank 2
        ]

        result = engine.fuse(lexical, semantic, top_k=10)

        # Document 1 should have highest score (rank 1 in both)
        assert result[0]["id"] == "1"

    def test_rrf_only_lexical(self):
        """Should handle documents only in lexical results."""
        engine = FusionEngine(fusion_method="rrf")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = []

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["id"] == "1"
        assert result[0]["lexical_rank"] == 1

    def test_rrf_score_breakdown(self):
        """Should include RRF breakdown."""
        engine = FusionEngine(fusion_method="rrf", rrf_k=100)

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        breakdown = result[0]["score_breakdown"]
        assert "lexical_rrf" in breakdown
        assert "semantic_rrf" in breakdown
        assert breakdown["fusion_method"] == "rrf"
        assert breakdown["rrf_k"] == 100


class TestInterpolationFusion:
    """Test interpolation fusion method."""

    def test_interpolate_both_scores(self):
        """Should use weights when both scores present."""
        engine = FusionEngine(fusion_method="interpolate", lexical_weight=0.7, semantic_weight=0.3)

        lexical = [{"id": "1", "lexical_score": 1.0}]
        semantic = [{"id": "1", "semantic_score": 0.5}]

        result = engine.fuse(lexical, semantic, top_k=10)

        # score = 0.7 * 1.0 + 0.3 * 0.5 = 0.85
        assert result[0]["score"] == 0.85

    def test_interpolate_only_lexical(self):
        """Should use 1.0 weight for lexical when only lexical present."""
        engine = FusionEngine(fusion_method="interpolate")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = []

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["score"] == 0.8  # Only lexical

    def test_interpolate_only_semantic(self):
        """Should use 1.0 weight for semantic when only semantic present."""
        engine = FusionEngine(fusion_method="interpolate")

        lexical = []
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["score"] == 0.6  # Only semantic

    def test_interpolate_no_scores(self):
        """Should skip documents with no scores."""
        engine = FusionEngine(fusion_method="interpolate")

        lexical = [{"id": "1"}]  # No score
        semantic = [{"id": "2"}]  # No score

        result = engine.fuse(lexical, semantic, top_k=10)

        assert result == []

    def test_interpolate_score_breakdown(self):
        """Should include interpolation breakdown."""
        engine = FusionEngine(fusion_method="interpolate")

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = [{"id": "1", "semantic_score": 0.6}]

        result = engine.fuse(lexical, semantic, top_k=10)

        breakdown = result[0]["score_breakdown"]
        assert breakdown["fusion_method"] == "interpolate"
        assert breakdown["lexical"]["raw"] == 0.8
        assert breakdown["semantic"]["raw"] == 0.6


class TestFusionEngineMethods:
    """Test utility methods."""

    def test_update_weights(self):
        """Should update and normalize weights."""
        engine = FusionEngine(lexical_weight=0.5, semantic_weight=0.5)

        engine.update_weights(0.8, 0.2)

        assert engine.lexical_weight == 0.8
        assert engine.semantic_weight == 0.2

    def test_update_weights_normalize(self):
        """Should normalize when weights don't sum to 1."""
        engine = FusionEngine()

        engine.update_weights(4.0, 4.0)

        assert engine.lexical_weight == 0.5
        assert engine.semantic_weight == 0.5

    def test_set_fusion_method_valid(self):
        """Should set valid fusion method."""
        engine = FusionEngine()

        engine.set_fusion_method("rrf")

        assert engine.fusion_method == "rrf"

    def test_set_fusion_method_invalid(self):
        """Should log warning for invalid method but keep current."""
        engine = FusionEngine()

        with patch("app.hybrid.fusion.logger") as mock_logger:
            engine.set_fusion_method("invalid")

            mock_logger.warning.assert_called_once()
            # Should keep current method
            assert engine.fusion_method == "linear"

    def test_get_statistics(self):
        """Should return engine statistics."""
        engine = FusionEngine(
            lexical_weight=0.7,
            semantic_weight=0.3,
            fusion_method="rrf",
            rrf_k=100,
        )

        stats = engine.get_statistics()

        assert stats["lexical_weight"] == 0.7
        assert stats["semantic_weight"] == 0.3
        assert stats["fusion_method"] == "rrf"
        assert stats["rrf_k"] == 100
        assert "linear" in stats["supported_methods"]


class TestFusionEdgeCases:
    """Test edge cases."""

    def test_mixed_duplicate_ids(self):
        """Should handle documents with same ID but different data."""
        engine = FusionEngine()

        lexical = [{"id": "1", "lexical_score": 0.8, "title": "Lexical"}]
        semantic = [{"id": "1", "semantic_score": 0.6, "title": "Semantic"}]

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        # Second result should overwrite first (lexical_score should be from semantic)
        assert result[0]["semantic_score"] == 0.6

    def test_fusion_result_ordering(self):
        """Should sort by fused score."""
        engine = FusionEngine()

        lexical = [
            {"id": "1", "lexical_score": 0.3},
            {"id": "2", "lexical_score": 0.8},
            {"id": "3", "lexical_score": 0.5},
        ]
        semantic = [
            {"id": "1", "semantic_score": 0.9},
            {"id": "2", "semantic_score": 0.2},
            {"id": "3", "semantic_score": 0.7},
        ]

        result = engine.fuse(lexical, semantic, top_k=10)

        # Scores: 1=0.6, 2=0.5, 3=0.6
        # Should be sorted by score descending
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_single_source_results(self):
        """Should handle results from only one source."""
        engine = FusionEngine()

        lexical = [{"id": "1", "lexical_score": 0.8}]
        semantic = []

        result = engine.fuse(lexical, semantic, top_k=10)

        assert len(result) == 1
        assert result[0]["lexical_score"] == 0.8