"""Time-decayed workload per member.

Framework-agnostic, like the rest of ``chores.fairness``: no ``django`` or
``chores.models`` imports, no wall-clock reads. The caller adapts ORM rows
(completions, contribution credits) into :class:`WorkItem` values, passes the
household's :class:`~chores.fairness.FairnessParams` and an explicit ``now``,
and gets back a plain ``{member_id: float}`` map.

Workload per item
-----------------
The per-item workload is :func:`chores.fairness.workload_value` of the chore's
minutes and difficulty (or a precomputed ``value``), then multiplied by a
decay factor::

    factor = 0.5 ** (age_days / decay_half_life_days)

so an item exactly one half-life old counts for half, two half-lives for a
quarter, and so on.

Who the workload lands on
------------------------
- Normally the chore's ``owner_id`` carries the workload, whoever performed it.
- If the item is ``credited`` (a :class:`ContributionCredit` exists - another
  member covered it), the workload moves to the ``actor_id`` who did it and the
  owner carries none.
- A chore with no owner lands on the ``actor_id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from .weights import FairnessParams
from .workload import workload_value

_SECONDS_PER_DAY = 86_400.0


@dataclass(frozen=True)
class WorkItem:
    """One completed piece of work, as plain data.

    Provide either ``minutes`` + ``effort`` (difficulty on the 1..5 scale) or a
    precomputed ``value``; ``value`` wins when both are present. ``timestamp``
    and the caller's ``now`` must both be timezone-aware or both naive.
    """

    actor_id: int
    owner_id: int | None
    timestamp: datetime
    minutes: int | None = None
    effort: int | None = None
    value: float | None = None
    credited: bool = False

    def beneficiary_id(self) -> int:
        """The member whose workload tally this item adds to."""
        if self.credited or self.owner_id is None:
            return self.actor_id
        return self.owner_id

    def base_value(self, params: FairnessParams) -> float:
        if self.value is not None:
            return self.value
        return workload_value(self.minutes, self.effort, params)


def decay_factor(age_days: float, half_life_days: float) -> float:
    """``0.5 ** (age_days / half_life_days)`` - 1.0 at age 0, 0.5 at one half-life."""
    return 0.5 ** (age_days / half_life_days)


def member_workloads(
    items: Iterable[WorkItem],
    member_ids: Iterable[int],
    params: FairnessParams,
    now: datetime,
) -> dict[int, float]:
    """Return each member's decayed workload over whatever window ``items`` spans.

    Every id in ``member_ids`` appears in the result, ``0.0`` when the member
    has no matching work. Items whose beneficiary is not in ``member_ids`` are
    ignored (e.g. a former member).
    """
    totals: dict[int, float] = {mid: 0.0 for mid in member_ids}
    for item in items:
        beneficiary = item.beneficiary_id()
        if beneficiary not in totals:
            continue
        age_days = (now - item.timestamp).total_seconds() / _SECONDS_PER_DAY
        totals[beneficiary] += item.base_value(params) * decay_factor(
            age_days, params.decay_half_life_days
        )
    return totals


def who_is_ahead(workloads: Mapping[int, float]) -> int | None:
    """The member id carrying the most workload, or ``None`` on a tie / empty."""
    if not workloads:
        return None
    ranked = sorted(workloads.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(ranked) >= 2 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]
