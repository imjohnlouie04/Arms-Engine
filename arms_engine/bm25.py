"""Lightweight token-overlap scorer used for skill/task matching.

Provides a domain-agnostic ``score_tokens`` function that assigns a relevance
score between a query token set and a document token set.  The scoring combines:

* Exact-string containment bonus (query phrase found verbatim in document label)
* Token intersection with weighted boosts for name tokens vs. description tokens
* Shared-prefix bonus for morphological variants (e.g. "deploy" ↔ "deployment")

This replaces the hand-rolled scoring in ``session.py`` and can be reused by
any other module that needs lightweight text-relevance ranking without a
full IR dependency.
"""

import os
import re


def _tokenize(text, min_len=3):
    """Return a set of lowercase alphanumeric tokens of length >= *min_len*."""
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= min_len}


def score_tokens(
    query,
    label,
    description="",
    *,
    exact_match_bonus=8,
    name_token_weight=4,
    desc_token_weight=1,
    prefix_bonus=6,
    prefix_min_len=5,
    label_min_token_len=3,
    desc_min_token_len=4,
):
    """Return an integer relevance score for *query* against *label*/*description*.

    Parameters
    ----------
    query:
        The search text (e.g. task description).
    label:
        Primary identifier to match against (e.g. skill name).  Tokens receive
        a higher weight than description tokens.
    description:
        Optional supporting text.  Tokens receive *desc_token_weight*.
    exact_match_bonus:
        Score added when the normalised *label* appears verbatim inside *query*.
    name_token_weight:
        Per-token bonus for tokens shared between *query* and *label*.
    desc_token_weight:
        Per-token bonus for tokens shared between *query* and *description*.
    prefix_bonus:
        Score added when a query token and a label token share a common prefix
        of at least *prefix_min_len* characters.
    prefix_min_len:
        Minimum shared prefix length to trigger the prefix bonus.
    label_min_token_len / desc_min_token_len:
        Minimum token lengths used when tokenizing *label* / *description*.
    """
    query_lower = query.lower()
    label_lower = label.lower()

    score = 0

    if label_lower in query_lower:
        score += exact_match_bonus

    query_tokens = _tokenize(query, min_len=label_min_token_len)
    label_tokens = _tokenize(label_lower, min_len=label_min_token_len)
    desc_tokens = _tokenize(
        "{} {}".format(label_lower, description.lower()),
        min_len=desc_min_token_len,
    )

    score += name_token_weight * len(query_tokens & label_tokens)
    score += desc_token_weight * len(query_tokens & desc_tokens)

    for query_token in query_tokens:
        for label_token in label_tokens:
            shared_len = len(os.path.commonprefix([query_token, label_token]))
            if shared_len >= prefix_min_len:
                score += prefix_bonus
                break

    return score
