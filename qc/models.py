from dataclasses import dataclass, field


@dataclass
class RuleIssue:
    rag_id: str
    issue_type: str
    risk_level: str
    description: str
    suggestion: str
    detected_by: str = "rule"

    def to_dict(self):
        return {
            "rag_id": self.rag_id,
            "issue_type": self.issue_type,
            "risk_level": self.risk_level,
            "description": self.description,
            "suggestion": self.suggestion,
            "detected_by": self.detected_by,
        }


@dataclass
class RuleQCResult:
    issues: list[dict] = field(default_factory=list)
    issue_item_ids: set[str] = field(default_factory=set)
    checked_count: int = 0


@dataclass
class RouteDecision:
    rag_id: str
    route: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class RiskRouteResult:
    routed_items: list[dict] = field(default_factory=list)
    passed_items: list[dict] = field(default_factory=list)
    decisions: list[RouteDecision] = field(default_factory=list)

    @property
    def routed_ids(self):
        return {
            item.get("rag_id", "")
            for item in self.routed_items
            if isinstance(item, dict)
        }

    @property
    def passed_ids(self):
        return {
            item.get("rag_id", "")
            for item in self.passed_items
            if isinstance(item, dict)
        }
