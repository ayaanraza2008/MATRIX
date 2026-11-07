"""MATRIX Repository Intelligence Package."""
from core.repository_intelligence.evaluator import (
    RepositoryEvaluation,
    RepositoryEvaluator,
    evaluator,
)
from core.repository_intelligence.engine import (
    SelectionResult,
    CapabilityGap,
    RepositoryIntelligenceEngine,
    repo_intelligence,
)
from core.repository_intelligence.resource_guard import (
    ResourceGuard,
    resource_guard,
)

__all__ = [
    "RepositoryEvaluation",
    "RepositoryEvaluator",
    "evaluator",
    "SelectionResult",
    "CapabilityGap",
    "RepositoryIntelligenceEngine",
    "repo_intelligence",
    "ResourceGuard",
    "resource_guard",
]
