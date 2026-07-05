"""Unit tests for the in-memory rate limiter."""
import os
import sys
import time
import unittest

# Add the backend directory to the path so we can import rate_limiter
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from app.rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Rate limiter unit tests."""

    def setUp(self):
        self.limiter = RateLimiter(max_requests=3, window_seconds=60)

    def test_allows_requests_within_limit(self):
        """Should allow requests up to the limit."""
        for _ in range(3):
            self.assertTrue(self.limiter._check("client-1"))

    def test_rejects_requests_exceeding_limit(self):
        """Should reject requests once the limit is reached."""
        for _ in range(3):
            self.limiter._check("client-2")
        self.assertFalse(self.limiter._check("client-2"))

    def test_independent_per_client(self):
        """Each client should have an independent counter."""
        for _ in range(3):
            self.limiter._check("alice")
        self.assertTrue(self.limiter._check("bob"))
        self.assertTrue(self.limiter._check("bob"))
        self.assertTrue(self.limiter._check("bob"))
        self.assertFalse(self.limiter._check("bob"))

    def test_prune_expired_entries(self):
        """Expired entries should be pruned."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.05)
        self.assertTrue(limiter._check("client-3"))
        self.assertTrue(limiter._check("client-3"))
        self.assertFalse(limiter._check("client-3"))
        time.sleep(0.06)
        self.assertTrue(limiter._check("client-3"))

    def test_different_max_limits(self):
        """Should respect a higher limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            self.assertTrue(limiter._check("client-4"))
        self.assertFalse(limiter._check("client-4"))

    def test_single_request_allowed(self):
        """Even with limit=1, one request should pass."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        self.assertTrue(limiter._check("client-5"))
        self.assertFalse(limiter._check("client-5"))

    def test_unknown_client_fallback(self):
        """Fallback to 'unknown' should work."""
        self.assertTrue(self.limiter._check("unknown"))


if __name__ == "__main__":
    unittest.main()
