# Working agreement

Engineering-first / science-second project.

The project is developed through two human-supervised AI surfaces connected by a
shared GitHub repository:

- Mac Studio / macOS: Luiz + ChatGPT
- PC workstation / Ubuntu 24.04 / RTX 4090: Luiz + Claude Code in VS Code
- Shared persistent state: https://github.com/visgraf/f3d-vision

Luiz is the project lead and decision authority.

ChatGPT is the design, review, specification, and proposal surface.

Claude Code is the workstation implementation, execution, diagnosis, and measurement
surface.

GitHub is the normal handoff medium between the two.

## The loop

    Luiz sets direction
        ↓
    Chat reads the live repository, reasons about the next step, writes the
    specification/code/docs, checks what it can, and—when Luiz explicitly
    authorizes a repository write—commits the proposed change to the active branch
        ↓
    Luiz tells Claude Code to pull and execute the step
        ↓
    Claude Code runs it on the workstation, diagnoses failures, makes only
    delegated fixes, records measured results, commits, and pushes
        ↓
    Chat reads the resulting commits, reports, and diffs directly from GitHub
        ↓
    Luiz decides
        ↓
    repeat

Luiz remains in the loop for decisions, but should not have to act as a mechanical
file courier.

## Authority and responsibility

### Luiz

Luiz:

- sets scientific and architectural direction;
- decides when a proposal should be committed;
- decides whether a result is accepted;
- decides when the project moves to the next phase;
- mediates between Chat and Claude Code when judgment or clarification is required.

Neither AI surface makes an undelegated project decision.

### ChatGPT

Chat:

- reads the current GitHub repository before proposing changes;
- reasons about architecture, experiments, checks, and acceptance criteria;
- writes specifications, code, documentation, and workstation instructions;
- runs checks available in its environment;
- clearly states what it could not run;
- reviews Claude Code's committed reports and changes directly from GitHub;
- distinguishes proposed behavior from measured behavior.

Chat may read the repository routinely.

Chat writes to the repository only when Luiz has explicitly authorized a repository
write for the current task.

A Chat-authored commit is a **proposal**, not a workstation validation.

### Claude Code

Claude Code is the execution authority on the Ubuntu workstation.

It:

- pulls the exact active branch before starting;
- reads this working agreement and the step contract;
- runs commands in the prescribed order;
- reads actual console output rather than trusting exit status alone;
- diagnoses a failing check before modifying code;
- makes only fixes within the delegated scope;
- does not weaken checks, change acceptance criteria, or tune against evaluation truth;
- records measured quantities and their source;
- commits and pushes the resulting implementation/report;
- stops when a decision rule requires Luiz or Chat.

GPU, Blender, scene-asset, performance, and full workstation claims become
**measured facts only after workstation execution**.

## GitHub handoff

GitHub is the default transport.

The normal Chat → Code handoff is therefore:

1. Chat commits the proposed code/specification/documentation to the active branch.
2. Luiz tells Claude Code to pull.
3. Claude Code executes the committed contract.
4. Claude Code commits the report and any delegated fixes.
5. Chat reads those commits directly.

ZIP + SHA256 handoffs remain a fallback for situations where direct GitHub access is
unavailable or where an external package must be transferred exactly.

No result needs to be pasted between Chat and Code when it is already committed in
the repository.

After every Chat-authored GitHub handoff, Chat provides Luiz with a self-contained
Claude Code prompt in a fenced code block, ready to copy/paste.

## Branch policy

Development occurs on the explicitly active project branch.

Do not assume `main`.

Before changing anything, both Chat and Claude Code must identify the current active
branch and its head.

Normal development is forward-only:

- commit;
- push;
- revert if wrong;
- do not rewrite published history.

No PR gate is required unless Luiz explicitly introduces one.

A phase or architectural branch may be merged or superseded only by an explicit
project decision.

## Proposed versus measured

Every important claim belongs to one of three states:

- **PROPOSED** — designed or predicted, but not run on the workstation;
- **MEASURED** — produced by an identified command/run and recorded in a committed
  report or other durable source;
- **ASSUMED / ESTIMATED** — explicitly identified as such.

Never blur these categories.

A Chat commit may contain expected outputs.

Only an actual run may convert them into measured outputs.

## Two hard rules

1. **Measured, proposed, or assumed — never ambiguous.**

   Every numerical claim is explicitly one of:
   - measured from an identified run — say where;
   - proposed or expected but not yet workstation-validated — say so;
   - assumed or estimated — say so.

2. **Every tool ships a check that can fail.**

   A control, known answer, invariant, negative test, or behavioral comparator must
   be able to expose an incorrect implementation.

   A tool that cannot come out wrong has not been tested.

## Scientific steps and refactoring steps

Scientific work and structural refactoring have different visible products.

### Scientific / behavioral step

When meaningful, produce an inspectable visual or measurable result together with
the checks.

### Structural / migration / refactoring step

A visual result is not mandatory.

Instead, the change must provide machine-checkable evidence that preserved behavior
remains preserved.

For the sealed Classroom baseline this normally includes the relevant structural
checks and the committed golden behavioral comparator, with:

    MISMATCHES 0

unless the contract explicitly declares a deliberate behavioral change.

Refactoring must not silently become a scientific change.

## Current migration principle

The repository is in a migration/refactoring period.

The governing rule is:

    migrate behavior first; redesign structure second

The historical implementation under `tools/` is a compatibility baseline where the
current contracts say it is sealed.

New architecture should be organized around stable concepts under `fov3d`, not around
historical experiment lineage.

Refactoring is therefore part of the work, but preserved behavior must remain
measurable throughout the transition.

## Checks and acceptance criteria

A step contract should state:

- what is being changed;
- what is deliberately not being changed;
- commands to run;
- cost class of each command;
- expected checks;
- acceptance criteria;
- stop conditions;
- scope of permitted fixes;
- exactly which results must be recorded.

Acceptance criteria are declared before evaluation whenever tuning against the result
would compromise the experiment.

Checks must not be modified merely to make a failing implementation pass.

If the implementation and the check disagree, diagnose the cause first.

## Standing defaults and precedence

Unless a step contract explicitly says otherwise:

- Claude Code has standing permission to commit and push step results and delegated
  fixes to the active branch. Work outside that scope requires Luiz.
- If the contract does not state a scope of permitted fixes, the default is **no
  fixes**: diagnose, report, and stop.
- Phase contracts and reports follow the existing convention
  `docs/<phase>.md` and `docs/<phase>-report.md`.
- If the active branch is not named by the instruction or contract, ask rather than
  infer it from the current checkout.
- An overnight command runs only when the step contract explicitly authorizes it and
  gives its justification; otherwise ask Luiz first.
- `CLAUDE.md` supplies the standing project rules. A step contract specializes
  those rules but may not contradict them. If a conflict exists, stop and report it.

## Workstation fixes

Claude Code may repair an implementation defect when the step contract clearly
delegates that class of repair.

A repair must:

- be minimal;
- stay outside the acceptance criterion itself;
- be described explicitly;
- preserve the scientific intent;
- be committed;
- be distinguishable from the original proposed change when that distinction matters.

If the required repair changes architecture, scientific assumptions, thresholds,
evaluation semantics, or experiment design, stop and return the decision to Luiz and
Chat.

## Environment conventions

- Metres.
- The head is fixed; eyes rotate about their own centres.
- `EYE` is a Blender camera object: local -Z is gaze, local +Y is head up.
- Equirect `(u,v)` to EYE-frame direction:

      lon = (u - 0.5) * 2*pi
      lat = (0.5 - v) * pi

  with `v = 0` at the top row.

- Epipolar `(theta, phi)` of a head-frame direction:
  `theta` is measured from +X (the baseline);
  `phi = atan2(d_y, -d_z)` about X.
  Corresponding directions share `phi`;
  parallax `theta_R - theta_L > 0`.

- Python should remain plain and typed where useful. Avoid framework machinery unless
  it solves a demonstrated problem.

## Two interpreters

The two Python environments are not interchangeable.

Scripts run by:

    blender -b -P

use Blender's bundled Python and may assume only packages actually available there.

Host-side scripts use the repository `.venv`.

Do not infer that an import is valid in Blender because it works in the host
environment, or vice versa.

`blender -b -P` may exit successfully even when a Python script reports a failure.
Any Blender-side tool producing an artifact must make its own failure observable and
must cause a nonzero process result when appropriate.

## Cost classes

Commands belong to one of three cost classes:

- **Interactive** — under roughly 10 seconds.
  Normal development loop: checks, single fixations, small deterministic tests.

- **Batch** — under roughly 5 minutes.
  Run when scientifically or structurally justified.

- **Overnight** — longer work.
  Must be explicitly justified before execution and its durable result retained.

Develop and debug on the cheapest configuration that preserves the relevant behavior.
Run expensive/full configurations only when they produce a result that will actually
be reported or used.

## Repository as source of truth

A new Chat conversation should reconstruct the project from the repository and the
committed phase reports, not rely solely on conversational memory.

Conversation summaries are useful handoffs but are secondary sources.

Important scientific or architectural information learned only in chat should be
promoted into an appropriate committed document when it becomes part of the project
state.

Each completed phase should leave enough committed evidence that another session can
recover:

- the question;
- the contract;
- the implementation;
- the checks;
- the measured result;
- the conclusion;
- the next open question.

## Reports

Claude Code should commit a report for every substantial executed phase.

The report should include:

- exact branch and relevant commit ids;
- commands actually run;
- summary lines verbatim where useful;
- every failing gate that affected the work;
- measured numbers and the files/runs they came from;
- implementation repairs and why they were required;
- deviations from the original proposal;
- whether the acceptance condition passed;
- unresolved decisions.

Chat should review the committed report and relevant diff rather than rely on a
second-hand paraphrase when GitHub access is available.

## Generated artifacts

Regenerable renders, previews, `.blend` outputs, caches, and similar products should
not be committed unless a specific contract declares them durable reference assets.

If a command cheaply regenerates an artifact, the command and source data are the
durable record.

Large or expensive reference assets must be identified by provenance and checksum,
and stored according to the scene/asset policy of the repository.

## Final principle

The working process should optimize for:

    clear scientific decisions
    + reproducible behavior
    + cheap recovery
    + explicit authority
    + minimal human file shuffling

GitHub carries state.

Claude Code measures on the workstation.

Chat designs and reviews.

Luiz decides.
