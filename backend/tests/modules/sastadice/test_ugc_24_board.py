"""Placeholder tests for the planned 24-tile UGC board generator.

The implementation is not yet wired up in BoardGenerationService, so
these tests are intentionally minimal and only assert that the service
can be constructed. Detailed UGC board behavior will be covered once
the feature lands.
"""

from app.modules.sastadice.services.board_generation_service import BoardGenerationService


def test_ugc_board_service_constructs() -> None:
    """Service can be instantiated (smoke test until UGC board is implemented)."""
    service = BoardGenerationService()
    assert service is not None
