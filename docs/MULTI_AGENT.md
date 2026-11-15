# Multi-Agent execution contract

## Portfolio outcome

Demonstrate that multiple AI agents can build and review the ERP through explicit assignments, bounded authority and evidence that can be checked against GitHub state. A role is claimed only when a separate agent actually performed it.

Native Codex multi-agent capabilities were the default until M4.6; since M4.7 the work is done by Claude Code sessions and, where stated, their sub-agents (corrected 2026-11-06). Noodle is an optional tool and is judged by delivered evidence, not by its presence.

## Roles

- **Manager:** selects the approved issue, assigns work, protects scope, updates the checklist from evidence and opens the post-merge docs PR for its slice ([AGENTS.md](../AGENTS.md#documentation-updates)).
- **Implementer:** changes only the assigned files and records assumptions, commands, results and limitations.
- **Reviewer:** reads the completed change independently, applies Scrutinize and does not edit during the review pass. After sending its report, a Reviewer session takes no further work on that slice. Other work the owner gives it is a new task on its own branch, starting with Issue workflow step 1.
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
6. Documentation updated per [AGENTS.md](../AGENTS.md#documentation-updates), or the follow-up docs PR that will do it.

## Evidence

Per issue, keep links to the GitHub issue, branch/PR, commits, test or CI results, reviewer verdict and checklist update. Conversation claims alone are not completion evidence.

## Repair and escalation

- Default limit: two repair cycles for the same failed finding.
- **Owner's standing rules (from 2026-11-14, [Issue #119 comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)):**
  1. Low/info findings after the final review round may be recorded as known limits without asking, unless they make
     an acceptance criterion or the main goal fail.
  2. Documentation-only fixes (stale status, historical notes, PR body) may be made by the Manager without asking.
  3. Always ask the owner first for changes to code, workflows, scope, dependencies, `AGENTS.md` or
     `docs/MULTI_AGENT.md`.
- A third recurrence stops automatic repair and is escalated to the owner with evidence and options.
- Stop immediately for secrets, personal/real factory data, an unexpected destructive action, repository mismatch, authorization failure, scope expansion or conflicting instructions.
- Never bypass approvals, sandboxing, branch protection or failing checks to make progress appear complete.

## Merge and deployment gate

Only the owner decides to merge or deploy. An open PR, passing CI or checked task does not grant that permission.

Owner's standing rules (from 2026-11-14, [Issue #119 comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)):

4. The owner merges every PR on GitHub; the Manager does not merge. (Before 2026-11-14 a session could merge
   on the owner's explicit merge instruction for that PR, as `AGENTS.md` still describes — historical for new work.)
5. After a merge the Manager opens the post-merge docs PR immediately.
6. A new slice starts only when the owner approves it in a comment on its Issue.

## Progress rule

Update `docs/TASKS.md` only after the linked evidence exists. Partial, blocked and pending work remains unchecked.
