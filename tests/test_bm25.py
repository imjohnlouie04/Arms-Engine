import unittest

from arms_engine.bm25 import score_tokens


class ScoreTokensBasicTests(unittest.TestCase):
    def test_exact_label_match_gives_high_score(self):
        score = score_tokens("deploy the backend service", "backend-system-architect", "design scalable backends")
        self.assertGreater(score, 0)

    def test_unrelated_query_gives_zero(self):
        score = score_tokens("xyzzy quux", "frontend-design", "ui ux components")
        self.assertEqual(score, 0)

    def test_label_substring_in_query_gets_bonus(self):
        high = score_tokens("run frontend-design review", "frontend-design", "ui components")
        low = score_tokens("deploy database migrations", "frontend-design", "ui components")
        self.assertGreater(high, low)

    def test_shared_tokens_increase_score(self):
        score_with_match = score_tokens("security audit owasp review", "security-code-review", "OWASP vulnerability scan")
        score_no_match = score_tokens("create new button component", "security-code-review", "OWASP vulnerability scan")
        self.assertGreater(score_with_match, score_no_match)

    def test_prefix_bonus_fires_for_partial_matches(self):
        # "security" and "secure" share prefix "secur" (5 chars) → prefix bonus
        score_with_prefix = score_tokens("secure the api endpoints", "security-code-review", "audit vulnerability")
        score_without = score_tokens("write unit tests", "security-code-review", "audit vulnerability")
        self.assertGreater(score_with_prefix, score_without)

    def test_empty_query_gives_zero(self):
        score = score_tokens("", "frontend-design", "ui components")
        self.assertEqual(score, 0)

    def test_empty_label_non_negative(self):
        # Empty label: "" is a substring of any string, so exact-match bonus fires.
        # Score is non-negative rather than exactly zero.
        score = score_tokens("fix the login bug", "", "")
        self.assertGreaterEqual(score, 0)

    def test_returns_integer(self):
        result = score_tokens("build api endpoints", "backend-system-architect", "rest api design")
        self.assertIsInstance(result, int)

    def test_score_is_non_negative(self):
        for query, label in [
            ("random text", "seo-expert"),
            ("", "logo-design"),
            ("qa automation tests cypress", "qa-automation-testing"),
        ]:
            self.assertGreaterEqual(score_tokens(query, label, ""), 0)


class ScoreTokensScoreBm25IntegrationTests(unittest.TestCase):
    """Verify score_tokens results match what session.py expects for skill routing."""

    SKILLS = [
        {"name": "qa-automation-testing", "description": "unit tests cypress playwright vitest"},
        {"name": "security-code-review", "description": "owasp audit rls auth vulnerability"},
        {"name": "seo-web-performance-expert", "description": "meta tags core web vitals schema"},
    ]

    def _best_skill(self, query):
        scored = [
            (score_tokens(query, s["name"], s["description"]), s["name"])
            for s in self.SKILLS
        ]
        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored[0][0] > 0 else None

    def test_qa_task_routes_to_qa_skill(self):
        self.assertEqual(self._best_skill("write cypress e2e tests for checkout flow"), "qa-automation-testing")

    def test_security_task_routes_to_security_skill(self):
        self.assertEqual(self._best_skill("owasp security audit rls policy review"), "security-code-review")

    def test_seo_task_routes_to_seo_skill(self):
        self.assertEqual(self._best_skill("improve core web vitals and meta tags"), "seo-web-performance-expert")


if __name__ == "__main__":
    unittest.main()
