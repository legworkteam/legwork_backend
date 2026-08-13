"""Kakao social provider.

MVP mock: deterministic profile from the authorization code (see google.py).
Swap in a real Kakao token/userinfo exchange when credentials are available.
"""

import hashlib

from app.providers.social.base import SocialProfile, SocialProvider


class KakaoSocialProvider(SocialProvider):
    async def fetch_profile(
        self, authorization_code: str, redirect_uri: str | None
    ) -> SocialProfile:
        digest = hashlib.sha256(authorization_code.encode()).hexdigest()
        return SocialProfile(
            provider_user_id=f"kakao_{digest[:24]}",
            email=f"{digest[:12]}@kakao.mock",
            name="Kakao User",
        )
