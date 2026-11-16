# Multi-Agent execution contract

## Portfolio outcome

Demonstrate that multiple AI agents can build and review the ERP through explicit assignments, bounded authority and evidence that can be checked against GitHub state. A role is claimed only when a separate agent actually performed it.

Native Codex multi-agent capabilities were the default until M4.6; since M4.7 the work is done by Claude Code sessions and, where stated, their sub-agents (corrected 2026-11-06). Noodle is an optional tool and is judged by delivered evidence, not by its presence.

## Roles

- **Manager:** selects the approved issue, assigns work, protects scope, updates the checklist from evidence and records the facts known after a merge in the first commit of its next PR ([AGENTS.md](../AGENTS.md#documentation-updates)). ("opens the post-merge docs PR for its slice" held until 2026-11-16 — historical.)
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
6. Documentation updated per [AGENTS.md](../AGENTS.md#documentation-updates), or the next PR that will do it. ("or the follow-up docs PR that will do it" held until 2026-11-16 — historical.)

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
   on the owner's explicit merge instruction for that PR — historical. The note "as `AGENTS.md` still describes —
   historical for new work" held until 2026-11-15, when `AGENTS.md` marked that wording historical.)
5. After a merge, the Manager puts the checklist tick and closeout in the first commit of its next PR; no separate
   docs PR. If `main` CI fails, the Manager tells the owner once in chat. The last slice (M7.5) may have its own docs
   PR. (From 2026-11-16, [Issue #126 comment 6910189566](https://github.com/porntaned/ERP-for-Factory/issues/126#issuecomment-6910189566); "After a merge the Manager opens the post-merge docs PR immediately." held until
   2026-11-16 — historical.)
6. A new slice starts only when the owner approves it in a comment on its Issue. The owner's checker reviews the Issue
   before approval only when the work touches business code, the database or permissions. Documentation, diagrams and
   small CI changes are approved without that review. (Second and third sentences from 2026-11-16, [Issue #126 comment 6910189566](https://github.com/porntaned/ERP-for-Factory/issues/126#issuecomment-6910189566).)

Owner's standing rules 7–8 (from 2026-11-15, owner in chat; verbatim below):

7. **Review level.**
   - Documentation, diagrams and small CI changes need no separate reviewer session: the owner's checker reviews them at merge.
   - A change that touches business code, the database or permissions, and the final Scrutinize, gets an independent review by a separate session.
8. **No self-scheduled CI checks.** Do not set timers or check-ins to poll CI. Report once, when the PR is ready to merge, in this short form:
   - PR number;
   - head SHA;
   - the 3 checks, with their attempt;
   - whether the `pkill -9` fallback ran;
   - findings the owner must decide, or "ไม่มี" if there are none.

> 7. ระดับรีวิว: งานเอกสาร/diagram/CI เล็ก = ไม่ต้องมี reviewer session แยก (ผู้ตรวจของเจ้าของตรวจตอน merge)
>    งานแตะโค้ด business, ฐานข้อมูล, สิทธิ์ หรือ final scrutinize = independent review โดย session แยก
> 8. ไม่ตั้งเวลาเช็ก CI เอง รายงานครั้งเดียวเมื่อพร้อม merge ในรูปแบบสั้น: เลข PR, head SHA, check 3 ตัว (attempt),
>    ทางสำรอง pkill -9, finding ที่ต้องให้เจ้าของตัดสิน (ถ้าไม่มีให้เขียน "ไม่มี")

Owner's decisions on Issue #126 (2026-11-16, [Issue #126 comment 6910189566](https://github.com/porntaned/ERP-for-Factory/issues/126#issuecomment-6910189566); verbatim):

> อนุมัติ P1–P5
> D-P1: ใช่ status text แก้ทับได้ ไม่ต้องมีวันที่หรือข้อความเดิม
> D-P2: (a) ใช่ main CI fail ให้แจ้งเจ้าของในแชตครั้งเดียว (b) ใช่ งานสุดท้ายเปิด docs PR ได้ (c) ใช่ ยอมให้ติ๊กบน main ช้าได้ 1 PR
> D-P5: ไม่เกิน 60 บรรทัด
> D-การทำ: แยก 2 PR (A: P1 P2 P3 P5, B: P4) ทำหลัง merge PR #125 และก่อน M7.4; ไม่มี reviewer session แยก
> PR A ให้บันทึกผล main CI #305 (ผ่าน) ที่ยังค้างจาก PR #125 ด้วย

The resulting rules are in [AGENTS.md](../AGENTS.md#documentation-updates) (P1, P2, P5) and rules 5–6 above (P2, P3).

Earlier practice superseded by rules 7–8 (historical from 2026-11-15):
- Every slice up to Issue #119 had an independent review by a separate session.
- The Manager set check-ins (`send_later`) to poll CI.

## Progress rule

Update `docs/TASKS.md` only after the linked evidence exists. Partial, blocked and pending work remains unchecked.
