# ============================================================
# test_triple_filter.py — Unit Tests for Triple Quality Filter
# ============================================================
# These tests verify that our hallucination detection rules work
# correctly. Each test creates a triple (good or bad) and checks
# that the filter accepts or rejects it as expected.
#
# Run with: python -m pytest test_triple_filter.py -v
# ============================================================

import pytest
from pydantic import HttpUrl

from models.knowledge import KnowledgeTriple
from pipeline.triple_filter import (
    TripleFilter,
    FilterAction,
    check_not_punctuation,
    check_min_alpha_length,
    check_has_real_words,
    check_not_circular,
    check_predicate_is_meaningful,
    check_no_common_artifacts,
    score_triple_quality,
)


# Helper to create triples quickly
def make_triple(
    subject: str = "async function",
    predicate: str = "returns",
    object_: str = "Promise",
    confidence: float = 0.9,
) -> KnowledgeTriple:
    return KnowledgeTriple(
        subject=subject,
        predicate=predicate,
        object_=object_,
        source_url="https://developer.mozilla.org/en-US/docs/Test",
        confidence=confidence,
    )


# ============================================================
# TEST 1: Punctuation Detection
# ============================================================
class TestPunctuationCheck:
    """Rule 1: Reject triples with only punctuation/symbols."""

    def test_colon_triple_rejected(self):
        """The ':' → ':' → ':' triple should be caught."""
        triple = make_triple(subject=":", predicate=":", object_=":")
        passed, reason, _ = check_not_punctuation(triple)
        assert not passed
        assert "hallucination pattern" in reason

    def test_mixed_punctuation_rejected(self):
        """Punctuation mix like ':' → ':' → ',' should be caught."""
        triple = make_triple(subject=":", predicate=":", object_=",")
        passed, reason, _ = check_not_punctuation(triple)
        assert not passed

    def test_brackets_rejected(self):
        """Bracket-only values should be caught."""
        triple = make_triple(subject="()", predicate="=>", object_="{}")
        passed, _, _ = check_not_punctuation(triple)
        assert not passed

    def test_normal_triple_passes(self):
        """Normal concepts should pass."""
        triple = make_triple(subject="Promise", predicate="returns", object_="result")
        passed, _, _ = check_not_punctuation(triple)
        assert passed


# ============================================================
# TEST 2: Minimum Alpha Length
# ============================================================
class TestMinAlphaLength:
    """Rule 2: Each field must have at least 2 alphabetic chars."""

    def test_single_char_subject_rejected(self):
        """Single letter 'a' is too short."""
        triple = make_triple(subject="a", predicate="is_a", object_="thing")
        passed, reason, _ = check_min_alpha_length(triple)
        assert not passed
        assert "alpha chars" in reason

    def test_number_only_rejected(self):
        """Just a number '1' has 0 alpha chars."""
        triple = make_triple(subject="1", predicate="is", object_="2")
        passed, _, _ = check_min_alpha_length(triple)
        assert not passed

    def test_short_but_valid_passes(self):
        """'if' has 2 alpha chars — exactly the minimum."""
        triple = make_triple(subject="if", predicate="is_a", object_="statement")
        passed, _, _ = check_min_alpha_length(triple)
        assert passed


# ============================================================
# TEST 3: Real Words Check
# ============================================================
class TestRealWords:
    """Rule 3: Subject and object must have at least 1 real word."""

    def test_symbols_only_rejected(self):
        """Symbols like '---' have 0 words."""
        triple = make_triple(subject="---", predicate="is_a", object_="***")
        passed, _, _ = check_has_real_words(triple)
        assert not passed

    def test_single_word_passes(self):
        """One word is enough."""
        triple = make_triple(subject="Promise", predicate="is_a", object_="object")
        passed, _, _ = check_has_real_words(triple)
        assert passed


# ============================================================
# TEST 4: Circularity Check
# ============================================================
class TestCircularity:
    """Rule 4: Subject and object should not be nearly identical."""

    def test_identical_rejected(self):
        """Same subject and object = circular."""
        triple = make_triple(subject="async function", predicate="is_a", object_="async function")
        passed, reason, _ = check_not_circular(triple)
        assert not passed
        assert "too similar" in reason

    def test_near_identical_rejected(self):
        """Plural vs singular should be caught (high similarity)."""
        triple = make_triple(subject="async function", predicate="is_a", object_="async functions")
        passed, _, _ = check_not_circular(triple)
        assert not passed

    def test_different_concepts_pass(self):
        """Completely different concepts should pass."""
        triple = make_triple(subject="Promise", predicate="enables", object_="async programming")
        passed, _, _ = check_not_circular(triple)
        assert passed


# ============================================================
# TEST 5: Predicate Quality
# ============================================================
class TestPredicateQuality:
    """Rule 5: Predicate must be meaningful."""

    def test_colon_predicate_rejected(self):
        """A colon as predicate is not meaningful."""
        triple = make_triple(subject="foo", predicate=":", object_="bar")
        passed, reason, _ = check_predicate_is_meaningful(triple)
        assert not passed

    def test_single_char_predicate_rejected(self):
        """Single character predicate is too short."""
        triple = make_triple(subject="foo", predicate="a", object_="bar")
        passed, _, _ = check_predicate_is_meaningful(triple)
        assert not passed

    def test_word_predicate_passes(self):
        """Real words as predicates pass."""
        triple = make_triple(subject="foo", predicate="returns", object_="bar")
        passed, _, _ = check_predicate_is_meaningful(triple)
        assert passed

    def test_snake_case_predicate_passes(self):
        """Snake case like 'is_a' passes."""
        triple = make_triple(subject="foo", predicate="is_a", object_="bar")
        passed, _, _ = check_predicate_is_meaningful(triple)
        assert passed


# ============================================================
# TEST 6: Common Artifacts
# ============================================================
class TestCommonArtifacts:
    """Rule 6: Known LLM artifact patterns."""

    def test_all_very_short_rejected(self):
        """All fields ≤3 chars is suspicious."""
        triple = make_triple(subject="abc", predicate="is", object_="def")
        passed, reason, _ = check_no_common_artifacts(triple)
        assert not passed
        assert "very short" in reason

    def test_normal_triple_passes(self):
        """Normal triple with longer fields passes."""
        triple = make_triple(subject="Promise", predicate="returns", object_="result value")
        passed, _, _ = check_no_common_artifacts(triple)
        assert passed


# ============================================================
# TEST 7: Full Filter Integration
# ============================================================
class TestTripleFilterIntegration:
    """Test the full TripleFilter class."""

    def setup_method(self):
        self.filt = TripleFilter(min_confidence=0.3)

    def test_good_triple_accepted(self):
        """A well-formed triple should pass all filters."""
        triple = make_triple(
            subject="async function",
            predicate="returns",
            object_="Promise",
            confidence=0.9,
        )
        result = self.filt.filter_triple(triple)
        assert result.action == FilterAction.ACCEPTED
        assert result.score > 0.3

    def test_garbage_triple_rejected(self):
        """A garbage triple should be rejected."""
        triple = make_triple(
            subject=":",
            predicate=":",
            object_=":",
            confidence=0.9,
        )
        result = self.filt.filter_triple(triple)
        assert result.action == FilterAction.REJECTED
        assert result.reason is not None

    def test_low_confidence_rejected(self):
        """Below minimum confidence should be rejected."""
        triple = make_triple(confidence=0.1)
        result = self.filt.filter_triple(triple)
        assert result.action == FilterAction.REJECTED
        assert "confidence" in result.reason

    def test_batch_filtering(self):
        """Batch of mixed triples should be partially accepted."""
        triples = [
            make_triple(subject="Promise", predicate="enables", object_="async programming", confidence=0.9),
            make_triple(subject=":", predicate=":", object_=":", confidence=0.9),
            make_triple(subject="async function", predicate="returns", object_="Promise", confidence=0.85),
            make_triple(subject="a", predicate="b", object_="c", confidence=0.5),
            make_triple(subject="fetch API", predicate="performs", object_="HTTP requests", confidence=0.9),
        ]
        result = self.filt.filter_batch(triples)
        assert len(result.accepted) == 3  # Promise, async function, fetch API
        assert len(result.rejected) == 2  # colon garbage, too short
        assert result.stats["acceptance_rate"] == 0.6


# ============================================================
# TEST 8: Quality Scoring
# ============================================================
class TestQualityScoring:
    """Test that quality scores make sense."""

    def test_high_quality_triple_scores_well(self):
        """Descriptive triple with good confidence should score high."""
        triple = make_triple(
            subject="async function declaration",
            predicate="enables",
            object_="asynchronous programming patterns",
            confidence=0.95,
        )
        score = score_triple_quality(triple)
        assert score > 0.7

    def test_short_triple_scores_lower(self):
        """Short generic triple should score lower."""
        triple = make_triple(
            subject="if",
            predicate="is",
            object_="keyword",
            confidence=0.7,
        )
        score = score_triple_quality(triple)
        assert score < 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])