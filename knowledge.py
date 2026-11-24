"""Compatibility import only: retain original test/import hooks without duplicate logic."""
import sys
from backend.services import knowledge_service
sys.modules[__name__] = knowledge_service
