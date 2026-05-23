# Examen Chart Supervision Protocol

Use this protocol when supervising `examen/examen_respuestas.html`.

## Scope

This is a review protocol, not the dashboard implementation. It should be used by any agent before approving the exam deliverable.

## Required Checks

1. Run data QA:

```bash
.venv/bin/python -m pytest tests/test_examen_prepare_data.py
```

2. Capture rendered screenshots:

```bash
.venv/bin/python scripts/capture_examen_screenshots.py
```

3. Review generated files under:

```text
examen/screenshots/
```

4. Check browser console results in:

```text
examen/screenshots/console.json
```

## Rubric By Case

- Case 1: `Otros` must be visible; valid-vote and emitted-vote denominators must not be mixed.
- Case 2: no dual axis; no hidden scope difference between national and circumscription panels.
- Case 3: district-level scatter or bubble chart; no causal poverty-vote headline.
- Case 4: normalized metric such as `monto_por_obra`; raw amount cannot be the only ranking.
- Case 5: star and snowflake diagrams must be legible, with fact grain, keys, and cardinality checks.

## Reporting Format

Use this order:

```text
Blockers
- [case/tab] issue, evidence, suggested fix

Major Issues
- [case/tab] issue, evidence, suggested fix

Minor Issues
- [case/tab] issue, evidence, suggested fix

Verification
- command run and result
- screenshots reviewed
```

## Coordination

Use Beads for ownership. If another agent is editing the HTML, review via screenshots and tests first; only patch the HTML after the user asks for implementation.
