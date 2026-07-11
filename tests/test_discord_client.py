import json
import httpx
from bot.discord_client import DiscordClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://discord.com/api/v10")
    return DiscordClient(token="tok", http=http)


def test_fetch_messages_returns_id_and_content():
    def handler(request):
        assert request.headers["Authorization"] == "Bot tok"
        assert request.url.path == "/api/v10/channels/111/messages"
        assert request.url.params["limit"] == "100"
        return httpx.Response(200, json=[
            {"id": "1", "content": "hello"},
            {"id": "2", "content": "world"},
        ])
    client = _client(handler)
    msgs = client.fetch_messages("111", limit=100)
    assert msgs == [{"id": "1", "content": "hello"}, {"id": "2", "content": "world"}]


def test_post_embeds_sends_payload():
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "9"})
    client = _client(handler)
    client.post_embeds("222", [{"title": "T"}])
    assert seen["path"] == "/api/v10/channels/222/messages"
    assert seen["body"] == {"embeds": [{"title": "T"}]}
