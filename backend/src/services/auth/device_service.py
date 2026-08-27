import hashlib


class DeviceService:
    """Derives stable, non-secret device metadata from request headers."""

    def label_from_user_agent(self, user_agent: str | None) -> str | None:
        if not user_agent:
            return None
        return user_agent[:120]

    def hash_user_agent(self, user_agent: str | None) -> str | None:
        if user_agent is None:
            return None
        return hashlib.sha256(user_agent.encode()).hexdigest()
