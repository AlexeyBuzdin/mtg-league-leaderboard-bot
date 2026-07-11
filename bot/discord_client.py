from __future__ import annotations

import httpx

_API_BASE = "https://discord.com/api/v10"


class DiscordClient:
    def __init__(self, token: str, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(base_url=_API_BASE)
        self._headers = {"Authorization": f"Bot {token}"}

    def fetch_messages(self, channel_id: str, limit: int = 100) -> list[dict]:
        resp = self._http.get(
            f"/channels/{channel_id}/messages",
            params={"limit": limit},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    def post_embeds(self, channel_id: str, embeds: list[dict]) -> None:
        resp = self._http.post(
            f"/channels/{channel_id}/messages",
            json={"embeds": embeds},
            headers=self._headers,
        )
        resp.raise_for_status()
