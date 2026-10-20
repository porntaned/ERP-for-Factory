# Scrutinize review

Review each change as an outsider and trace its real behavior end to end.

## 1. Intent

State the goal in one sentence. Ask whether the change should exist and name any smaller solution that achieves the same result. Stop if the goal is underspecified.

## 2. Trace

Follow every claimed behavior through its actual entry point, calls, branches, state mutations and side effects. Include unchanged code at the seams. For plans, test assumptions against the existing repository. Record surprising paths.

## 3. Verify

For each claim, write the path and the observed result. Check invalid, empty, Unicode and large inputs; concurrency, retries and partial failures; performance, error and contract changes; and whether tests exercise the real path.

## 4. Report

Order findings by severity. Each finding must include:

- Finding with a file and line when applicable.
- Why it matters.
- Evidence from the traced path or input.
- The smallest concrete change.

Close with one verdict: `ship`, `fix-then-ship`, `rework` or `reject`, followed by the biggest reason.

## Rules

- No rubber stamps. If no defect is found, state exactly what was traced.
- Cite evidence for every code claim.
- Separate what a PR claims from what was verified.
- Always consider a simpler alternative.
- Do not bury structural problems under style comments.
- Identify self-review and independent review accurately.
