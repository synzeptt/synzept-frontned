from app.services.memory_feed.service import MemoryFeedService


def test_memory_feed_returns_five_to_seven_ranked_cards():
    feed = MemoryFeedService().get_feed()

    assert 5 <= len(feed.cards) <= 7
    assert all(card.score is not None for card in feed.cards)


def test_memory_feed_pinned_cards_are_ranked_first():
    feed = MemoryFeedService().get_feed()

    assert feed.cards[0].pinned is True
    assert feed.cards[0].type == "recent_decision"


def test_memory_feed_filters_snoozed_and_archived_cards():
    data = {
        "generatedAt": "2026-07-07T08:45:00+05:30",
        "nextRefreshAt": "2026-07-08T08:00:00+05:30",
        "refreshLabel": "Daily refresh ready tomorrow at 8:00 AM",
        "cards": [
            {
                "id": "active",
                "type": "open_loop",
                "title": "Active card",
                "summary": "Visible",
                "detail": "Visible detail",
                "source": "Mock",
                "timestamp": "2026-07-07T08:45:00+05:30",
                "tags": [],
                "factors": [{"label": "Relevance", "value": 90}],
            },
            {
                "id": "snoozed",
                "type": "open_loop",
                "title": "Snoozed card",
                "summary": "Hidden",
                "detail": "Hidden detail",
                "source": "Mock",
                "timestamp": "2026-07-07T08:45:00+05:30",
                "tags": [],
                "status": "snoozed",
                "factors": [{"label": "Relevance", "value": 100}],
            },
            {
                "id": "archived",
                "type": "open_loop",
                "title": "Archived card",
                "summary": "Hidden",
                "detail": "Hidden detail",
                "source": "Mock",
                "timestamp": "2026-07-07T08:45:00+05:30",
                "tags": [],
                "status": "archived",
                "factors": [{"label": "Relevance", "value": 100}],
            },
        ],
    }

    feed = MemoryFeedService(data).get_feed(limit=5)

    assert [card.id for card in feed.cards] == ["active"]


def test_memory_feed_score_uses_weighted_factors_and_pin_boost():
    card = {
        "factors": [
            {"label": "Relevance", "value": 100},
            {"label": "Urgency", "value": 80},
            {"label": "Importance", "value": 80},
            {"label": "Recency", "value": 60},
            {"label": "Feedback", "value": 40},
        ]
    }
    pinned_card = {**card, "pinned": True}

    assert MemoryFeedService.score_card(card) == 81.0
    assert MemoryFeedService.score_card(pinned_card) == 93.0
