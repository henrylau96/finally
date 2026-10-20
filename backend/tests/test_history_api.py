from app import main


async def test_simulator_history_is_empty(client):
    """The simulator has no history."""
    response = await client.get("/api/history/AAPL")
    assert response.status_code == 200
    assert response.json() == []


async def test_history_passes_uppercased_ticker(client, monkeypatch):
    """The route normalizes the ticker and returns the source's points."""
    seen = []
    points = [{"time": 1, "value": 2.0}, {"time": 2, "value": 3.0}]

    async def fake(ticker):
        seen.append(ticker)
        return points

    monkeypatch.setattr(main.source, "history", fake)
    response = await client.get("/api/history/aapl")
    assert response.json() == points
    assert seen == ["AAPL"]


async def test_history_rejects_invalid_ticker(client):
    """Non-letter or too-long tickers are 422."""
    for bad in ("123", "TOOLONG"):
        response = await client.get(f"/api/history/{bad}")
        assert response.status_code == 422
        assert "detail" in response.json()
