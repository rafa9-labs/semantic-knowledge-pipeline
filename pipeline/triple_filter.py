# ============================================================
# pipeline/triple_filter.py — Triple Quality Filter & Hallucination Detector
# ============================================================
# This module is our DEFENSE against LLM hallucinations and garbage data.
#
# THE PROBLEM:
#   LLMs sometimes extract "triples" that are meaningless garbage:
#     (":", ":", ":")           ← punctuation, not concepts
#     (":", ":", ",")           ← same issue
#     ("a", "is_a", "thing")   ← too vague to be useful
#     ("foo", "bar", "foo")    ← subject = object (circular)
#
# THE SOLUTION:
#   We apply a series of RULE-BASED filters (no LLM needed — fast & free):
#     1. Character check: reject triples with only punctuation/symbols
#     2. Length check: reject triples that are too short to be meaningful
#     3. Vocabulary check: reject triples with no real words
#     4. Circularity check: reject triples where subject ≈ object
#     5. Semantic check: reject triples with no alphabetic characters
#     6. Common hallucination patterns: known bad patterns from LLMs
#
# WHY NOT USE THE LLM TO FILTER?
#   - Speed: regex checks take microseconds; LLM calls take seconds
#   - Cost: free vs. LLM API costs
#   - Reliability: deterministic rules > another LLM call (which could hallucinate too)
#   - Separation of concerns: the LLM extracts, deterministic code validates
#
# Each filter returns a reason string if the triple is rejected, or None if it passes.
# We log the rejection reason so we can tune the filters over time.
# ============================================================

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from models.knowledge import KnowledgeTriple

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# FILTER RESULT — Why a triple was accepted or rejected
# ----------------------------------------------------------
class FilterAction(Enum):
    """What happened to a triple after filtering."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class FilterResult:
    """
    Result of filtering a single triple.

    Attributes:
        triple: The original triple that was evaluated.
        action: Whether it was ACCEPTED or REJECTED.
        reason: If rejected, WHY it was rejected (for debugging/tuning).
        score: A quality score from 0.0 (garbage) to 1.0 (excellent).
            Used to rank triples when we have too many.
    """
    triple: KnowledgeTriple
    action: FilterAction
    reason: Optional[str] = None
    score: float = 1.0


@dataclass
class BatchFilterResult:
    """
    Result of filtering a batch of triples.

    Attributes:
        results: Individual filter results for each triple.
        accepted: List of triples that passed all filters.
        rejected: List of (triple, reason) pairs that were rejected.
        stats: Counts of accepted/rejected per filter rule.
    """
    results: list[FilterResult] = field(default_factory=list)
    accepted: list[KnowledgeTriple] = field(default_factory=list)
    rejected: list[tuple[KnowledgeTriple, str]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def acceptance_rate(self) -> float:
        """What percentage of triples passed the filters."""
        total = len(self.accepted) + len(self.rejected)
        if total == 0:
            return 0.0
        return len(self.accepted) / total


# ----------------------------------------------------------
# HALLUCINATION DETECTION RULES
# ----------------------------------------------------------
# Each rule is a simple function that checks one aspect of a triple.
# If the triple fails the check, it returns a rejection reason string.
# If it passes, it returns None (no issues found).

# Known punctuation-only patterns that Gemma 4 tends to produce.
# These are NOT real concepts — they're artifacts of the LLM
# misinterpreting table-of-contents or code syntax in MDN pages.
HALLUCINATION_PATTERNS = [
    r"^[:\-,;.\s]+$",           # Only punctuation and whitespace
    r"^[^a-zA-Z0-9]+$",         # No alphanumeric characters at all
    r"^\W+$",                    # Only non-word characters
    r"^\s*\d+\s*$",             # Just a number
    r"^[\[\](){}<>]+$",         # Only brackets
]

# Minimum number of ALPHABETIC characters a field must have
# to be considered a real concept. "a" = 1 char (too short).
# "async function" = 13 chars (good). We count only letters.
MIN_ALPHA_CHARS = 2

# Minimum number of WORDS (sequences of letters) in a field.
# A single word like "Promise" is OK, but single characters are not.
MIN_WORDS = 1

# Maximum similarity between subject and object before we call it circular.
# e.g., "async function" vs "async function" = 100% → REJECT
SIMILARITY_THRESHOLD = 0.8


def _count_alpha_chars(text: str) -> int:
    """Count the number of alphabetic characters in a string."""
    return sum(1 for c in text if c.isalpha())


def _count_words(text: str) -> int:
    """Count the number of word tokens (sequences of letters/digits)."""
    return len(re.findall(r'[a-zA-Z0-9]+', text))


def _normalize_for_comparison(text: str) -> str:
    """
    Normalize text for similarity comparison.

    Lowercase, strip whitespace, remove punctuation.
    "Async Function" → "asyncfunction"
    """
    return re.sub(r'[^a-zA-Z0-9]', '', text.lower())


def _jaccard_similarity(a: str, b: str) -> float:
    """
    Calculate Jaccard similarity between two strings.

    Jaccard = (intersection of character bigrams) / (union of character bigrams)
    Returns 0.0 (completely different) to 1.0 (identical).

    Why bigrams (character pairs)?
      - More robust than exact match
      - Catches "async function" vs "async functions" (high similarity)
      - But distinguishes "Promise" vs "fetch" (low similarity)
    """
    if not a or not b:
        return 0.0

    # Create character bigrams (pairs of adjacent characters)
    bigrams_a = set(a[i:i+2] for i in range(len(a) - 1))
    bigrams_b = set(b[i:i+2] for i in range(len(b) - 1))

    if not bigrams_a or not bigrams_b:
        return 0.0

    intersection = bigrams_a & bigrams_b
    union = bigrams_a | bigrams_b

    return len(intersection) / len(union)


# ----------------------------------------------------------
# THE FILTER RULES
# ----------------------------------------------------------
# Each function takes a triple and returns (passed: bool, reason: str|None, score_penalty: float)

def check_not_punctuation(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 1: Reject triples where subject, predicate, or object
    is only punctuation/symbols.

    Catches: (":", ":", ":"), (",", ":", ":"), etc.
    These happen when the LLM misinterprets code syntax or tables.
    """
    for field_name, field_value in [
        ("subject", triple.subject),
        ("predicate", triple.predicate),
        ("object_", triple.object_),
    ]:
        for pattern in HALLUCINATION_PATTERNS:
            if re.match(pattern, field_value):
                return False, f"{field_name} matches hallucination pattern: '{field_value}'", 0.0

    return True, None, 0.0


def check_min_alpha_length(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 2: Each field must have at least MIN_ALPHA_CHARS alphabetic characters.

    Catches: ("a", "is_a", "b"), ("1", "returns", "2")
    Real concepts have at least 2 letters: "if", "fn", "Promise"
    """
    for field_name, field_value in [
        ("subject", triple.subject),
        ("predicate", triple.predicate),
        ("object_", triple.object_),
    ]:
        alpha_count = _count_alpha_chars(field_value)
        if alpha_count < MIN_ALPHA_CHARS:
            return (
                False,
                f"{field_name} has only {alpha_count} alpha chars (min {MIN_ALPHA_CHARS}): '{field_value}'",
                0.0,
            )

    return True, None, 0.0


def check_has_real_words(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 3: Subject and object must each contain at least MIN_WORDS real word(s).

    Catches: ("---", "is_a", "***"), entries that are all symbols.
    "Promise" has 1 word ✓, "async function" has 2 words ✓, ":" has 0 words ✗
    """
    for field_name, field_value in [
        ("subject", triple.subject),
        ("object_", triple.object_),
    ]:
        word_count = _count_words(field_value)
        if word_count < MIN_WORDS:
            return (
                False,
                f"{field_name} has {word_count} words (min {MIN_WORDS}): '{field_value}'",
                0.0,
            )

    return True, None, 0.0


def check_not_circular(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 4: Subject and object should not be nearly identical.

    Catches: ("async function", "is_a", "async function")
    A triple where subject ≈ object tells us nothing about the relationship.
    We use Jaccard similarity on character bigrams for fuzzy matching.
    """
    norm_subj = _normalize_for_comparison(triple.subject)
    norm_obj = _normalize_for_comparison(triple.object_)

    similarity = _jaccard_similarity(norm_subj, norm_obj)

    if similarity > SIMILARITY_THRESHOLD:
        return (
            False,
            f"subject and object are too similar ({similarity:.0%}): "
            f"'{triple.subject}' vs '{triple.object_}'",
            0.0,
        )

    return True, None, 0.0


def check_predicate_is_meaningful(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 5: Predicate must contain at least one alphabetic character
    and be at least 2 characters long.

    Catches: (":", ":", ","), ("foo", ":", "bar")
    Predicates should be words like "is_a", "returns", "enables", etc.
    """
    pred = triple.predicate.strip()

    if len(pred) < 2:
        return False, f"predicate too short ({len(pred)} chars): '{pred}'", 0.0

    if not any(c.isalpha() for c in pred):
        return False, f"predicate has no letters: '{pred}'", 0.0

    return True, None, 0.0


def check_no_common_artifacts(triple: KnowledgeTriple) -> tuple[bool, Optional[str], float]:
    """
    Rule 6: Reject known LLM artifact patterns.

    Common patterns that LLMs produce from MDN pages:
      - Navigation breadcrumbs: "Home > Docs > ..."
      - Table of contents markers
      - Code syntax artifacts: "=>" "()" "{}" etc.
      - Version numbers without context: "ES2017", "2027"
    """
    # Check for pure code syntax in subject/object
    code_patterns = [
        r'^[(){}\[\]<>]+$',       # Only brackets
        r'^[=><!&|]+$',           # Only operators
        r'^\W+$',                  # Only non-word chars (already checked but double-safe)
    ]

    for field_name, field_value in [
        ("subject", triple.subject),
        ("object_", triple.object_),
    ]:
        for pattern in code_patterns:
            if re.match(pattern, field_value.strip()):
                return (
                    False,
                    f"{field_name} looks like code syntax artifact: '{field_value}'",
                    0.0,
                )

    # Reject if ALL three fields are extremely short (≤ 3 chars each)
    # Real knowledge triples have at least one descriptive field
    all_short = (
        len(triple.subject.strip()) <= 3
        and len(triple.predicate.strip()) <= 3
        and len(triple.object_.strip()) <= 3
    )
    if all_short:
        return (
            False,
            f"all fields are very short (≤3 chars): "
            f"'{triple.subject}', '{triple.predicate}', '{triple.object_}'",
            0.0,
        )

    return True, None, 0.0


def score_triple_quality(triple: KnowledgeTriple) -> float:
    """
    Score a triple's quality from 0.0 (poor) to 1.0 (excellent).

    This is a HEURISTIC score based on multiple signals:
      - Confidence score from the LLM (30% weight)
      - Field descriptiveness — longer, more specific = better (30% weight)
      - Predicate quality — real words like "enables" > symbols (20% weight)
      - Source reliability — we trust the LLM's own confidence (20% weight)

    Used to RANK triples when we have many and want the best ones.
    """
    score = 0.0

    # Factor 1: LLM confidence (0.0-1.0) — weighted 30%
    score += triple.confidence * 0.30

    # Factor 2: Subject descriptiveness — longer = more specific = better
    # But cap at 30 chars (diminishing returns for very long subjects)
    subj_len = min(len(triple.subject.strip()), 30)
    score += (subj_len / 30.0) * 0.15

    # Factor 3: Object descriptiveness — same logic
    obj_len = min(len(triple.object_.strip()), 30)
    score += (obj_len / 30.0) * 0.15

    # Factor 4: Predicate has real words (not symbols)
    has_alpha = any(c.isalpha() for c in triple.predicate)
    pred_words = _count_words(triple.predicate)
    if has_alpha and pred_words >= 1:
        score += 0.20

    # Factor 5: Subject and object are different enough (not circular)
    norm_subj = _normalize_for_comparison(triple.subject)
    norm_obj = _normalize_for_comparison(triple.object_)
    similarity = _jaccard_similarity(norm_subj, norm_obj)
    diversity_bonus = 1.0 - similarity  # More different = better
    score += diversity_bonus * 0.20

    return round(min(score, 1.0), 3)


# ----------------------------------------------------------
# THE MAIN FILTER CLASS
# ----------------------------------------------------------

class TripleFilter:
    """
    Filters knowledge triples to remove hallucinations and low-quality data.

    USAGE:
        filter = TripleFilter()
        result = filter.filter_batch(triples)
        print(f"Accepted: {len(result.accepted)}")
        print(f"Rejected: {len(result.rejected)}")
        for triple, reason in result.rejected:
            print(f"  REJECTED: {triple.subject} — {reason}")

    DESIGN DECISION:
        We use multiple independent rules rather than one complex rule.
        This makes it easy to:
          - Add new rules
          - Disable specific rules
          - Debug which rule caught a specific triple
          - Tune individual thresholds
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        max_triples_per_source: int = 50,
    ):
        """
        Initialize the TripleFilter.

        Args:
            min_confidence: Triples below this LLM confidence are auto-rejected.
                0.3 = allow somewhat uncertain triples (they might be valid).
            max_triples_per_source: Safety cap — if one source produces
                an absurd number of triples, something went wrong.
        """
        self.min_confidence = min_confidence
        self.max_triples_per_source = max_triples_per_source

        # The filter rules, in order of execution.
        # Order matters: cheap/fast rules first, expensive ones later.
        self.rules = [
            ("punctuation_check", check_not_punctuation),
            ("min_alpha_length", check_min_alpha_length),
            ("predicate_meaningful", check_predicate_is_meaningful),
            ("real_words", check_has_real_words),
            ("not_circular", check_not_circular),
            ("common_artifacts", check_no_common_artifacts),
        ]

    def filter_triple(self, triple: KnowledgeTriple) -> FilterResult:
        """
        Apply all filter rules to a single triple.

        Returns a FilterResult with:
          - action: ACCEPTED or REJECTED
          - reason: Why it was rejected (if it was)
          - score: Quality score (0.0-1.0)
        """
        # Pre-check: minimum confidence threshold
        if triple.confidence < self.min_confidence:
            return FilterResult(
                triple=triple,
                action=FilterAction.REJECTED,
                reason=f"confidence {triple.confidence} below minimum {self.min_confidence}",
                score=0.0,
            )

        # Run each rule in order. First failure → immediate rejection.
        for rule_name, rule_func in self.rules:
            passed, reason, penalty = rule_func(triple)
            if not passed:
                return FilterResult(
                    triple=triple,
                    action=FilterAction.REJECTED,
                    reason=f"[{rule_name}] {reason}",
                    score=penalty,
                )

        # All rules passed! Calculate quality score.
        quality_score = score_triple_quality(triple)

        return FilterResult(
            triple=triple,
            action=FilterAction.ACCEPTED,
            reason=None,
            score=quality_score,
        )

    def filter_batch(self, triples: list[KnowledgeTriple]) -> BatchFilterResult:
        """
        Filter a batch of triples and return detailed results.

        This is the main entry point for the pipeline.
        It applies all rules to each triple and collects statistics.

        Args:
            triples: List of KnowledgeTriple objects to filter.

        Returns:
            BatchFilterResult with accepted/rejected lists and stats.
        """
        result = BatchFilterResult()
        rejection_counts: dict[str, int] = {}

        for triple in triples:
            filter_result = self.filter_triple(triple)
            result.results.append(filter_result)

            if filter_result.action == FilterAction.ACCEPTED:
                result.accepted.append(triple)
            else:
                result.rejected.append((triple, filter_result.reason or "unknown"))

                # Track which rule caught the most triples (for tuning)
                # Extract rule name from "[rule_name] detail..." format
                rule_name = "other"
                if filter_result.reason and filter_result.reason.startswith("["):
                    rule_name = filter_result.reason.split("]")[0][1:]
                rejection_counts[rule_name] = rejection_counts.get(rule_name, 0) + 1

        # Safety cap: if one source produced way too many triples
        if len(result.accepted) > self.max_triples_per_source:
            logger.warning(
                f"Too many triples accepted ({len(result.accepted)}), "
                f"capping at {self.max_triples_per_source} by quality score"
            )
            # Sort by quality score (highest first) and take the top N
            scored = [
                (score_triple_quality(t), t)
                for t in result.accepted
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            result.accepted = [t for _, t in scored[:self.max_triples_per_source]]

        result.stats = {
            "total_input": len(triples),
            "accepted": len(result.accepted),
            "rejected": len(result.rejected),
            "acceptance_rate": result.acceptance_rate,
            "rejections_by_rule": rejection_counts,
        }

        logger.info(
            f"Triple filter: {len(triples)} input → "
            f"{len(result.accepted)} accepted, {len(result.rejected)} rejected "
            f"({result.acceptance_rate:.0%} pass rate)"
        )

        if rejection_counts:
            logger.info(f"Rejection breakdown: {rejection_counts}")

        return result