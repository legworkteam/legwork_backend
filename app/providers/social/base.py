"""SocialProvider interface.

AuthService exchanges an authorization code for a normalized SocialProfile via
this contract, so Google/Kakao (or a mock) are interchangeable.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SocialProfile:
    provider_user_id: str
    email: str | None
    name: str


class SocialProvider(Protocol):
    async def fetch_profile(
        self, authorization_code: str, redirect_uri: str | None
    ) -> SocialProfile: ...
