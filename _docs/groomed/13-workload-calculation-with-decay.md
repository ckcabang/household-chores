# Workload calculation with decay

## Goal

`chores/fairness/` exposes a pure function that, given completions,
contribution credits, and a household's fairness weights, returns each
member's time-decayed workload over a window — with no Django imports.

## Acceptance criteria

- [ ] A `chores/fairness/` package exists (`__init__.py`) holding the workload
      function, with unit tests in `chores/tests/`.
- [ ] The function takes plain data (dataclasses / dicts / tuples), not model
      instances: per work item it needs the acting member id, the owner id, the
      minutes and effort (or a precomputed workload value), and a timestamp;
      plus the weights (time/difficulty weighting, `decay_half_life_days`) and a
      `now` reference passed in by the caller.
- [ ] Workload per item combines time and difficulty per the weights, by a
      formula documented in the module.
- [ ] Decay: an item's contribution is multiplied by
      `0.5 ** (age_days / half_life_days)`; an item exactly one half-life old
      counts half — pinned by a test.
- [ ] A contribution credit moves that item's workload from the owner to the
      helper (helper accrues it, owner does not) — pinned by a test.
- [ ] The return value maps every member id passed in to a float, including
      `0.0` for a member with no activity.
- [ ] Unit tests over fixed inputs cover: one completion, two balanced members,
      decay at 0 / 1 / 2 half-lives, a credited completion, and empty input.
- [ ] `import chores.fairness` triggers no Django settings access; the fairness
      tests run without a database.

## Out of scope

- Choosing owners / assignment — task #14.
- Any view or template — the balance is rendered by task #17.
- Persisting the computed workload — it is computed on read
  (`_docs/tech-stack-decision.md`).

## Constraints

- No Django imports anywhere in `chores/fairness/`. Views and commands adapt
  ORM objects into the function's plain inputs.
- Deterministic and side-effect free: no wall-clock reads inside the function —
  the caller passes `now`.
