"""Propose a primary owner for each upcoming chore, toward equal workload.

Framework-agnostic, like the rest of ``chores.fairness``. The caller passes
the chores to place (each with a workload ``cost`` from
:func:`chores.fairness.workload_value` and its current ``owner_id``), the
current per-member workload (from :func:`chores.fairness.member_workloads`),
and the household's people-to-chore constraints. It gets back, per chore, the
proposed owner (or ``unassignable``) plus the projected workload for each
member after the proposal.

Algorithm
---------
Greedy, deterministic:

1. Order chores by decreasing ``cost``, ties broken by ascending ``id``.
2. For each chore, the eligible members are those not ``exclude``d for it. No
   eligible member -> the chore is ``unassignable`` (never forced onto anyone).
3. Among the eligible, pick the one with the lowest projected workload. Ties
   break toward a member who ``prefer``s the chore, then toward the lower id.
4. Add the chore's cost to the chosen member's projected workload and continue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

PREFER = "prefer"
EXCLUDE = "exclude"


@dataclass(frozen=True)
class AssignableChore:
    id: int
    cost: float
    owner_id: int | None = None


@dataclass(frozen=True)
class ChoreProposal:
    chore_id: int
    current_owner_id: int | None
    proposed_owner_id: int | None
    unassignable: bool = False


@dataclass(frozen=True)
class AssignmentResult:
    proposals: list[ChoreProposal] = field(default_factory=list)
    projected: dict[int, float] = field(default_factory=dict)

    def proposed_owner(self, chore_id: int) -> int | None:
        for proposal in self.proposals:
            if proposal.chore_id == chore_id:
                return proposal.proposed_owner_id
        return None


def propose_assignments(
    chores: Iterable[AssignableChore],
    workloads: Mapping[int, float],
    constraints: Sequence[tuple[int, int, str]] = (),
    member_ids: Iterable[int] | None = None,
) -> AssignmentResult:
    """Return an :class:`AssignmentResult` for ``chores``.

    ``constraints`` is a sequence of ``(member_id, chore_id, kind)`` triples
    with ``kind`` in ``{"prefer", "exclude"}``. ``member_ids`` defaults to the
    keys of ``workloads``.
    """
    chores = list(chores)
    members = list(member_ids) if member_ids is not None else list(workloads)
    projected: dict[int, float] = {m: float(workloads.get(m, 0.0)) for m in members}

    excluded: set[tuple[int, int]] = set()
    preferred: set[tuple[int, int]] = set()
    for member_id, chore_id, kind in constraints:
        if kind == EXCLUDE:
            excluded.add((chore_id, member_id))
        elif kind == PREFER:
            preferred.add((chore_id, member_id))

    ordered = sorted(chores, key=lambda c: (-c.cost, c.id))
    proposals: list[ChoreProposal] = []
    for chore in ordered:
        eligible = [m for m in members if (chore.id, m) not in excluded]
        if not eligible:
            proposals.append(
                ChoreProposal(
                    chore_id=chore.id,
                    current_owner_id=chore.owner_id,
                    proposed_owner_id=None,
                    unassignable=True,
                )
            )
            continue
        chosen = min(
            eligible,
            key=lambda m: (
                projected[m],
                0 if (chore.id, m) in preferred else 1,
                m,
            ),
        )
        projected[chosen] += chore.cost
        proposals.append(
            ChoreProposal(
                chore_id=chore.id,
                current_owner_id=chore.owner_id,
                proposed_owner_id=chosen,
            )
        )

    return AssignmentResult(proposals=proposals, projected=projected)
