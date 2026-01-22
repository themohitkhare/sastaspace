"""Game service - backward compatibility wrapper."""
from app.modules.sastadice.services.game_orchestrator import GameOrchestrator

# Backward compatibility alias
GameService = GameOrchestrator
