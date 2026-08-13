"""Google social provider.

MVP mock: derives a deterministic profile from the authorization code so the
account create/login flow works without real Google credentials. Replace
`fetch_profile` with a real token-exchange + userinfo call when keys exist.
"""

import hashlib

from app.providers.social.base import SocialProfile, SocialProvider


class GoogleSocialProvider(SocialProvider):
    async def fetch_profile(
        self, authorization_code: str, redirect_uri: str | None
    ) -> SocialProfile:
        digest = hashlib.sha256(authorization_code.encode()).hexdigest()
        return SocialProfile(
            provider_user_id=f"google_{digest[:24]}",
            email=f"{digest[:12]}@gmail.mock",
            name="Google User",
        )
