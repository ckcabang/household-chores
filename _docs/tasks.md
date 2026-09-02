# Backlog

Tasks for the MVP defined in [`plan.md`](plan.md). Stack and structure are set by
[`tech-stack-decision.md`](tech-stack-decision.md): Django 5.1, server-rendered templates
with HTMX + Alpine, fairness logic in a framework-agnostic `chores/fairness/` module.

Each task is scoped to a single working session and written to stand on its own — where a
task builds on data or code from an earlier one, its description says what it assumes so
you don't have to read the rest. The numbering is a suggested order, not a hard chain.

---

## 1. Project skeleton with a passing test
Goal: A fresh clone can install dependencies and run the test suite green.
Description: The Django project (`config/`) and `chores` app are already scaffolded. Add a test runner (pytest + pytest-django, or the built-in Django runner), a single trivial passing test, and a documented one-line command to run the suite. Add a GitHub Actions workflow that installs `requirements.txt` and runs the tests on every push.

## 2. Environment-based settings and Postgres support
Goal: Settings come from environment variables; Postgres works in production, SQLite locally.
Description: Introduce a settings module that reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL` from the environment, keeping SQLite as the zero-config local default. Add a `.env.example` listing every variable with safe placeholder values. Document the variables in the README.

## 3. Base layout and front-end shell
Goal: A shared page template with navigation, styling, and HTMX + Alpine loaded.
Description: Create `base.html` with a header, nav, content block, and footer, plus a small stylesheet and the HTMX and Alpine libraries (vendored into static files). Add a placeholder home view and route so the shell is visible. Later UI tasks extend this template.

## 4. User accounts
Goal: A visitor can sign up, log in, and log out.
Description: Use Django's auth system with a signup form and view, and Django's built-in login/logout views wired to templates that extend the base layout. Redirect authenticated users landing on signup/login to the home page. No household logic in this task.

## 5. Household creation
Goal: A signed-in user can create a household and become its first member.
Description: Add `Household` and `Membership` models, enforcing at most two memberships per household and at most one household per user. Provide a "create household" view that creates the household and the creator's membership, then redirects to the home page. Register both models in the Django admin.

## 6. Invitation flow
Goal: A household member can invite exactly one other person with a signed link.
Description: Assuming `Household` and `Membership` exist, add an `Invitation` model and a view that produces a signed, expiring invite URL. Opening a valid link while logged in (signing up first if needed) adds the user as the second member; links to an already-full household are rejected with a clear message. Register the model in the admin.

## 7. Chore management
Goal: Household members can create, edit, and delete chores.
Description: Add a `Chore` model with name, description, cadence in days, estimated minutes, difficulty rating, a primary-owner membership, and an "allows multiple contributors" flag. Build list, create, edit, and delete views scoped to the current user's household. Register the model in the admin.

## 8. People-to-chore constraints
Goal: Members can mark a person as preferred or excluded for a specific chore.
Description: Assuming `Chore` and `Membership` exist, add a `Constraint` model linking a membership to a chore with a type of `prefer` or `exclude`. Provide UI to add and remove constraints. This task only needs storage and management UI; the assignment algorithm consumes these records later.

## 9. Chore occurrences
Goal: Each chore generates dated occurrences that form its history.
Description: Assuming `Chore` exists, add a `ChoreOccurrence` model with a due date, a status of `active` or `completed`, and a completed timestamp. Add a function and a management command that generate any missing occurrences for a chore across a date window from its cadence. Overdue is never stored — treat an active occurrence with a past due date as overdue when displaying.

## 10. Completing an occurrence
Goal: A member can mark an occurrence done and optionally log actual time and effort.
Description: Assuming `ChoreOccurrence` exists, add a `Completion` model (occurrence, the member who did it, optional actual minutes, optional actual effort). Add a "mark done" action that flips the occurrence to completed and stores the completion. This is the raw data later consumed by fairness and estimate-learning features.

## 11. Claiming and helper credit
Goal: When someone other than the owner does a chore, they receive recorded contribution credit.
Description: Assuming `ChoreOccurrence` and `Completion` exist, add a `ContributionCredit` model recording that member A did work owned by member B, with a workload value and timestamp. Add a "claim" action and extend completion so a non-owner completing an occurrence creates a credit. No fairness math here — only accurate capture.

## 12. Fairness weights
Goal: Each household has stored, editable fairness weights.
Description: Assuming `Household` exists, add a `FairnessWeights` model (one row per household) holding factors such as time-vs-difficulty weighting and a decay half-life, seeded with defaults when a household is created. Provide a simple edit screen. Approval rules for weight changes are handled by a separate task.

## 13. Workload calculation with decay
Goal: A pure function returns each member's time-decayed workload over a window.
Description: In `chores/fairness/`, implement a function that takes completions, contribution credits, and a household's fairness weights and returns per-member workload totals with time decay applied. Cover it with unit tests over fixed inputs. No model or view changes beyond reading existing data.

## 14. Automatic assignment
Goal: A pure function proposes a primary owner for each upcoming chore.
Description: Assuming the workload function and the `Constraint` model exist, implement an assignment function that takes chores, the current workload balance, and prefer/exclude constraints, and returns a proposed owner per chore that moves the household toward equal workload while honoring hard exclusions. Unit-test with small scenarios and expose it behind a "rebalance" view that shows proposed changes without applying them.

## 15. Estimate-learning proposals
Goal: The system proposes updated time and difficulty estimates from history.
Description: Assuming `Completion` and `Chore` exist, add an `EstimateProposal` model and a function that compares logged actual times against a chore's current estimate and, past a configurable threshold, produces a proposed new estimate with a short rationale. Show pending proposals in the UI; either member can accept one individually, which updates the chore.

## 16. Weight-change proposals with approval
Goal: Fairness-weight changes take effect only after both members approve.
Description: Assuming `FairnessWeights` and `Membership` exist, add a `WeightProposal` model holding proposed values and each member's approval state. Provide UI to create, view, and approve or reject a proposal. On mutual approval, apply the values to the household's weights; otherwise leave them unchanged.

## 17. Dashboard
Goal: One screen showing current and upcoming chores, ownership and status, fairness balance, and history.
Description: Assuming chores, occurrences, completions, and the workload function exist, build a dashboard view that lists current and upcoming occurrences with owner and status (including derived overdue), shows the current fairness balance between the two members, and gives a short historical-contribution summary. Read-only apart from a "mark done" shortcut.

## 18. AI setup — plan generation
Goal: Turn a questionnaire plus a free-text description into a structured household plan.
Description: Add a form collecting guided answers and a free-form household description, then call the Anthropic API with a JSON schema to produce a chore list, cadences, time and difficulty estimates, inferable constraints, an initial assignment plan, and a reasoning summary. Store the raw response as a draft and validate it against the schema. Nothing is applied to the household in this task.

## 19. AI setup — review and apply
Goal: Members review the generated plan and apply it to their household.
Description: Assuming a validated draft plan from the generation task exists, build a review screen showing the generated chores, estimates, constraints, and proposed assignments alongside the AI's reasoning. Members can edit or drop items, then confirm. On confirm, create the real `Chore` and `Constraint` records; chores and estimates activate immediately while assignments are flagged as needing review.

## 20. Admin coverage and demo data
Goal: Every model is usable in the Django admin, and a demo household can be built with one command.
Description: Give all models admin registrations with useful list displays, filters, and search. Add a management command that creates a demo household with two users, several chores, generated occurrences, and some completion history for local testing and screenshots.

## 21. Production deployment configuration
Goal: The app can be built and run in a production-like environment.
Description: Add a `Dockerfile` (or `Procfile`), configure static file serving with WhiteNoise, and run the app under Gunicorn. Verify `python manage.py check --deploy` passes with production settings and document the deploy steps in the README.
