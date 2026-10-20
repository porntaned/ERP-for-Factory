# Multi-Agent execution contract

## Portfolio outcome

Demonstrate that multiple AI agents can build and review the ERP through explicit assignments, bounded authority and evidence that can be checked against GitHub state. A role is claimed only when a separate agent actually performed it.

Native Codex multi-agent capabilities are the default. Noodle is an optional tool and is judged by delivered evidence, not by its presence.

## Roles

- **Manager:** selects the approved issue, assigns work, protects scope and updates the checklist from evidence.
- **Implementer:** changes only the assigned files and records assumptions, commands, results and limitations.
- **Reviewer:** reads the completed change independently, applies Scrutinize and does not edit during the review pass.
- **Verifier:** runs the required checks in the approved environment and records the tested commit SHA. One agent may verify its own work, but that is labelled self-verification.

## Assignment contract

Every assignment identifies the repository, issue, branch, base/head SHA when available, in-scope files, acceptance criteria, prohibited actions and expected evidence. Agents may not infer permission to merge, deploy, expose secrets, access real factory data or write another repository.

## Handoff

A handoff records:

1. Task and role actually performed.
2. Files and behavior changed.
3. Commands, environment and exact results.
4. Commit SHA or a clear statement that work is not committed.
5. Findings, remaining risks and the next responsible role.

## Evidence

Per issue, keep links to the GitHub issue, branch/PR, commits, test or CI results, reviewer verdict and checklist update. Conversation claims alone are not completion evidence.

## Repair and escalation

- Default limit: two repair cycles for the same failed finding.
- A third recurrence stops automatic repair and is escalated to the owner with evidence and options.
- Stop immediately for secrets, personal/real factory data, an unexpected destructive action, repository mismatch, authorization failure, scope expansion or conflicting instructions.
- Never bypass approvals, sandboxing, branch protection or failing checks to make progress appear complete.

## Merge and deployment gate

Only the owner decides to merge or deploy. An open PR, passing CI or checked task does not grant that permission.

## Progress rule

Update `docs/TASKS.md` only after the linked evidence exists. Partial, blocked and pending work remains unchecked.
