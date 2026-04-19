"""Static role to permission mapping for JWT claims and frontend guards."""

from __future__ import annotations

from app.core.enums import UserRole

ROLE_PERMISSIONS: dict[str, list[str]] = {
    UserRole.PLATFORM_ADMIN.value: [
        "admin:*",
        "lender:*",
        "customer:*",
        "payment:*",
        "report:*",
        "subscription:*",
        "user:*",
    ],
    UserRole.OWNER.value: [
        "lender:dashboard",
        "loan:read",
        "loan:write",
        "customer:read",
        "customer:write",
        "payment:review",
        "user:manage",
        "report:read",
    ],
    UserRole.MANAGER.value: [
        "lender:dashboard",
        "loan:read",
        "loan:write",
        "customer:read",
        "customer:write",
        "payment:review",
        "report:read",
    ],
    UserRole.REVIEWER.value: [
        "lender:dashboard",
        "loan:read",
        "customer:read",
        "payment:review",
        "report:read",
    ],
    UserRole.AGENT.value: [
        "lender:dashboard",
        "loan:read",
        "customer:read",
        "customer:write",
        "payment:submit",
    ],
    UserRole.CUSTOMER.value: [
        "me:read",
        "loan:read_own",
        "payment:submit_own",
    ],
}


def get_permissions_for_role(role: str) -> list[str]:
    """Return permissions associated with a role identifier."""
    return ROLE_PERMISSIONS.get(role, []).copy()
