from apps.config import AgentLimits
from apps.server.tools.base import Principal, Tool


def denied(tool: Tool, principal: Principal, limits: AgentLimits) -> str | None:
    # Confirmation UI/proof is deliberately absent in Phase 3. The model cannot supply it.
    if tool.permission == "sensitive":
        return "permission_denied"
    if tool.requires_confirmation:
        return "confirmation_required"
    if (tool.permission == "low_risk" or tool.mutates) and not (
        limits.allow_mutations and principal.allow_mutations
    ):
        return "permission_denied"
    return None
