import logging

from rest_framework.throttling import ScopedRateThrottle

logger = logging.getLogger(__name__)


class LoggedScopedRateThrottle(ScopedRateThrottle):
    """DRF's per-scope rate limit, logging every refused request so repeated attempts show up in the logs."""

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        if not allowed:
            logger.warning("Rate limit hit: %s from %s", self.scope, self.get_ident(request))
        return allowed
