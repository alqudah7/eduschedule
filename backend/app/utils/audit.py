"""AuditLog write helper.

Every audit row belongs to a school. The rule (MULTITENANT.md §7):

  * A SCHOOL_ADMIN or TEACHER acting inside their own tenant writes to
    that tenant's AuditLog. school_id = the actor's own school_id.

  * A SUPER_ADMIN acting on ANOTHER tenant (e.g. resetting a user's
    password inside Sunrise Academy while the super_admin belongs to
    the platform tenant) writes to the ACTED-ON tenant's AuditLog.
    The point is that a super_admin cannot silently touch a school
    without evidence appearing in that school's own log — the tenant's
    own admins should be able to see it without a support ticket.

There is deliberately no "global" audit log. Every action is attributable
to exactly one school, and that school always sees it.

Usage:

    from app.utils.audit import write_audit_log

    write_audit_log(
        db,
        actor=current_user,
        action="CREATE_TEACHER",
        details=f"Created {teacher.name}",
        target_school_id=teacher.school_id,
    )

If ``target_school_id`` is omitted, it defaults to the actor's own school
— which is the right thing 99% of the time. Pass it explicitly for
super_admin flows.
"""
from __future__ import annotations

from typing import Optional

import cuid
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.alert import AuditLog


def write_audit_log(
    db: Session,
    *,
    actor,
    action: str,
    details: str,
    target_school_id: Optional[int] = None,
) -> AuditLog:
    """Record an auditable action against a school.

    The write happens under a scoped SET LOCAL app.current_school_id so
    the RLS policy admits the insert into the target school's slice of
    the table — otherwise a super_admin whose session GUC points at 0
    (get_admin_db) would fail the WITH CHECK clause on AuditLog.

    Returns the persisted row. Caller is responsible for db.commit().
    """
    if target_school_id is None:
        target_school_id = actor.school_id

    if target_school_id is None:
        # Actor has no tenant AND caller did not pass one. That's a bug
        # — audit rows must live in exactly one tenant. Raise loudly
        # rather than silently drop the log.
        raise ValueError(
            "write_audit_log: no target_school_id and actor has no school_id"
        )

    is_cross_tenant = target_school_id != actor.school_id

    if is_cross_tenant:
        if actor.role != "SUPER_ADMIN":
            raise PermissionError(
                "Only SUPER_ADMIN may write an audit row to a school "
                "other than their own",
            )
        # The RLS write policy on AuditLog is
        # ``WITH CHECK (school_id = current_setting('app.current_school_id'))``,
        # so a super_admin whose ambient GUC is 0 (cross-tenant scope)
        # must temporarily rebind the GUC to the target school for the
        # insert to be admitted.
        db.execute(text("SET LOCAL app.current_school_id = :sid"),
                   {"sid": str(target_school_id)})

    # Format the actor prefix so the target school's admins can tell
    # at a glance that a super_admin from outside touched their data.
    actor_label = actor.email
    if is_cross_tenant:
        actor_label = f"{actor.email} (SUPER_ADMIN, cross-tenant)"

    row = AuditLog(
        id=cuid.cuid(),
        action=action,
        actor=actor_label,
        details=details,
        school_id=target_school_id,
    )
    db.add(row)
    return row
