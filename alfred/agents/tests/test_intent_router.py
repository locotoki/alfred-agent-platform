"""Tests for Intent Router."""

import pytest

from alfred.agents.intent_router import Intent, IntentRouter


class TestIntent:
    """Test Intent dataclass."""

    def test_intent_creation(self):
        """Test creation of Intent objects with attributes."""
        intent = Intent(
            type="greeting",
            confidence=0.95,
            entities={"name": "John"},
            raw_message="Hello John",
        )

        assert intent.type == "greeting"
        assert intent.confidence == 0.95
        assert intent.entities == {"name": "John"}
        assert intent.raw_message == "Hello John"

    def test_intent_string_representation(self):
        """Test string representation of Intent objects."""
        intent = Intent(type="help", confidence=0.87, entities={}, raw_message="I need help")

        assert str(intent) == "Intent(type=help, confidence=0.87)"


class TestIntentRouter:
    """Test IntentRouter functionality."""

    @pytest.fixture
    def router(self):
        """Return a new IntentRouter instance for testing."""
        return IntentRouter()

    def test_route_greeting_intent(self, router):
        """Test routing of greeting messages."""
        test_messages = ["Hello", "Hi there", "Hey!", "Good morning", "Greetings"]

        for message in test_messages:
            intent = router.route(message)
            assert intent.type == "greeting"
            assert intent.confidence == 0.9
            assert intent.raw_message == message

    def test_route_help_intent(self, router):
        """Test routing of help messages."""
        test_messages = [
            "Help",
            "I need assistance",
            "How to use this?",
            "What can you do?",
            "Guide me",
        ]

        for message in test_messages:
            intent = router.route(message)
            assert intent.type == "help"
            assert intent.confidence == 0.9

    def test_route_status_intent(self, router):
        """Test routing of status check messages."""
        test_messages = [
            "Status",
            "Health check",
            "Ping",
            "Are you alive?",
            "Is it working?",
        ]

        for message in test_messages:
            intent = router.route(message)
            assert intent.type == "status_check"
            assert intent.confidence == 0.9

    def test_route_unknown_intent(self, router):
        """Test routing of unrecognized messages."""
        test_messages = [
            "Random gibberish",
            "Something completely different",
            "Unrelated query",
            "12345",
            "!@#$%",
        ]

        for message in test_messages:
            intent = router.route(message)
            assert intent.type == "unknown"
            assert intent.confidence == 0.0

    def test_case_insensitive_routing(self, router):
        """Test that routing is case-insensitive."""
        variations = ["HELLO", "Hello", "hello", "HeLLo"]

        for message in variations:
            intent = router.route(message)
            assert intent.type == "greeting"

    def test_register_custom_handler(self, router):
        """Test registering a custom handler."""

        def custom_handler(intent):
            return "Custom response"

        # Register handler and pattern separately
        router.register_handler("custom_intent", custom_handler)
        router.register_pattern("custom_intent", r"custom|special")

        # Test custom intent routing
        intent = router.route("This is custom")
        assert intent.type == "custom_intent"

    def test_handler_access(self, router):
        """Test handler access via handle method."""
        # Create an intent
        intent = Intent(type="greeting", confidence=0.9, entities={}, raw_message="Hello")

        # Use the handle method
        response = router.handle(intent)
        assert response is not None

    def test_default_handlers_responses(self, router):
        """Test responses from default handlers."""
        # Test greeting response
        greeting_intent = router.route("Hello")
        response = router.handle(greeting_intent)
        assert response is not None

        # Test help response
        help_intent = router.route("Help")
        response = router.handle(help_intent)
        assert response is not None

        # Test unknown response
        unknown_intent = router.route("Random gibberish")
        response = router.handle(unknown_intent)
        assert response is not None

    def test_error_handling_in_route(self, router, monkeypatch):
        """Test error handling during routing."""
        # Create a test pattern that's deliberately invalid

        import re

        invalid_pattern = re.compile(r"(unclosed")
        monkeypatch.setattr(router, "_patterns", {"error_pattern": invalid_pattern})

        # This should handle the error gracefully
        intent = router.route("Test message")
        assert intent.type == "unknown"

    def test_prometheus_metrics_increment(self, router):
        """Test that Prometheus metrics are incremented correctly."""
        # Note: In a real test, you'd use prometheus_client.REGISTRY
        # to check actual metric values

        from alfred.agents.intent_router import intents_total

        # Reset metrics
        intents_total._metrics.clear()

        # Route several messages
        test_cases = [
            ("Hello", "greeting"),
            ("Help me", "help"),
            ("Unknown stuff", "unknown"),
        ]

        for message, expected_intent in test_cases:
            intent = router.route(message)
            assert intent.type == expected_intent

            # Check metric
            metric_value = intents_total.labels(
                intent_type=intent.type, status="processed"
            ).get_value()
            assert metric_value == 1.0

    def test_three_sample_messages(self, router):
        """Test the acceptance criteria: 3 sample messages → correct stub intents."""
        test_cases = [
            ("Hello Alfred", "greeting"),
            ("I need help with something", "help"),
            ("Random message", "unknown"),
        ]

        for message, expected_intent in test_cases:
            intent = router.route(message)
            assert intent.type == expected_intent
            assert intent.raw_message == message
