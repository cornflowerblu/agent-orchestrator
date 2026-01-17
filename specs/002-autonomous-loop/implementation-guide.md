# Implementation Guide: Autonomous Loop Execution

**Branch**: `002-autonomous-loop` | **Date**: 2026-01-17

## Quick Start

### Prerequisites
- tasks.md generated (122 tasks across 8 phases)
- Virtual environment activated: `source .venv/bin/activate`
- Tests passing: `pytest -m "not integration"`

---

## Option 1: Sequential Implementation (Single Developer)

### Step 1: Complete Setup + Foundational
```bash
/ralph "Implement Phase 1 Setup tasks (T001-T006) and Phase 2 Foundational tasks (T007-T023) from specs/002-autonomous-loop/tasks.md" --max-iterations 50
```

### Step 2: Complete US1 (P1)
```bash
/ralph "Implement US1 tasks (T024-T040) following TDD workflow" --max-iterations 50
```

### Step 3: Complete US3 (P1)
```bash
/ralph "Implement US3 tasks (T041-T058) following TDD workflow" --max-iterations 50
```

### Step 4: Complete US2 (P2)
```bash
/ralph "Implement US2 tasks (T059-T075) following TDD workflow" --max-iterations 50
```

### Step 5: Complete US4 (P2)
```bash
/ralph "Implement US4 tasks (T076-T095) following TDD workflow" --max-iterations 50
```

### Step 6: Complete US5 (P3)
```bash
/ralph "Implement US5 tasks (T096-T111) following TDD workflow" --max-iterations 50
```

### Step 7: Polish
```bash
/ralph "Implement Polish tasks (T112-T122)" --max-iterations 30
```

---

## Option 2: Parallel Implementation (Multiple Sessions)

### What Are Git Worktrees?

Git worktrees let you have **multiple working directories from the same repo** - perfect for parallel development:

```
~/Development/
├── agent-orchestrator/          # Main worktree (your current directory)
├── agent-orchestrator-us2/      # Worktree for US2 development
├── agent-orchestrator-us3/      # Worktree for US3 development
└── agent-orchestrator-us4/      # Worktree for US4 development
```

**Key benefits:**
- Each worktree is a full working directory
- All share the same `.git` (no cloning needed)
- You can run multiple Claude sessions simultaneously
- Changes don't conflict until you merge

### Parallel Execution Plan

```
Phase 1 (Setup) ─── Sequential
      ↓
Phase 2 (Foundational) ─── Sequential, BLOCKS all stories
      ↓
┌─────┴─────┐
↓           ↓
US1       US3      ← PARALLEL (both P1, different modules)
  ↓         ↓
  └────┬────┘
       ↓
┌──────┴──────┐
↓             ↓
US2         US4    ← PARALLEL (both P2, different modules)
  ↓           ↓
  └─────┬─────┘
        ↓
      US5          ← Sequential (needs all above)
        ↓
      Polish       ← Sequential
```

### Step 1: Complete Setup + Foundational (Main Worktree)

```bash
# In main directory
cd /Users/rurich/Development/agent-orchestrator

/ralph "Implement Phase 1 (T001-T006) and Phase 2 (T007-T023)" --max-iterations 50

# Commit the foundational work
/commit
```

### Step 2: Create Worktrees for Parallel US1 + US3

```bash
# Create worktrees (from main directory)
git worktree add ../agent-orch-us1 002-autonomous-loop
git worktree add ../agent-orch-us3 002-autonomous-loop
```

### Step 3: Run US1 and US3 in Parallel

**Terminal 1 (US1):**
```bash
cd ../agent-orch-us1
source .venv/bin/activate

# Run ralph for US1
/ralph "Implement US1 tasks (T024-T040) from specs/002-autonomous-loop/tasks.md following TDD workflow" --max-iterations 50
```

**Terminal 2 (US3):**
```bash
cd ../agent-orch-us3
source .venv/bin/activate

# Run ralph for US3
/ralph "Implement US3 tasks (T041-T058) from specs/002-autonomous-loop/tasks.md following TDD workflow" --max-iterations 50
```

### Step 4: Merge US1 and US3 Back

```bash
# Back in main worktree
cd /Users/rurich/Development/agent-orchestrator

# Create commits in worktrees first (if not done)
cd ../agent-orch-us1 && /commit
cd ../agent-orch-us3 && /commit

# Merge changes (use git cherry-pick or merge)
cd /Users/rurich/Development/agent-orchestrator
git merge --no-ff ../agent-orch-us1
git merge --no-ff ../agent-orch-us3

# Or use cherry-pick for specific commits
git log --oneline ../agent-orch-us1
git cherry-pick <commit-hash>

# Remove worktrees when done
git worktree remove ../agent-orch-us1
git worktree remove ../agent-orch-us3
```

### Step 5: Create Worktrees for Parallel US2 + US4

```bash
git worktree add ../agent-orch-us2 002-autonomous-loop
git worktree add ../agent-orch-us4 002-autonomous-loop
```

**Terminal 1 (US2):**
```bash
cd ../agent-orch-us2
source .venv/bin/activate
/ralph "Implement US2 tasks (T059-T075)" --max-iterations 50
```

**Terminal 2 (US4):**
```bash
cd ../agent-orch-us4
source .venv/bin/activate
/ralph "Implement US4 tasks (T076-T095)" --max-iterations 50
```

### Step 6: Merge and Complete US5

```bash
# Merge US2 and US4
cd /Users/rurich/Development/agent-orchestrator
# ... merge as above ...

# Complete US5 (sequential, needs all above)
/ralph "Implement US5 tasks (T096-T111)" --max-iterations 50
```

---

## Alternative: Using /speckit.implement

Instead of calling ralph directly, you can use speckit.implement which reads tasks.md automatically:

```bash
# Implement specific phase
/speckit.implement   # Then specify "Phase 3 - US1"

# Or wrap with ralph-loop for self-correction
/ralph-loop "/speckit.implement" --completion-promise "PHASE_COMPLETE" --max-iterations 50
```

---

## Task Ranges Reference

| Phase | Story | Tasks | Count |
|-------|-------|-------|-------|
| 1 | Setup | T001-T006 | 6 |
| 2 | Foundational | T007-T023 | 17 |
| 3 | US1 | T024-T040 | 17 |
| 4 | US3 | T041-T058 | 18 |
| 5 | US2 | T059-T075 | 17 |
| 6 | US4 | T076-T095 | 20 |
| 7 | US5 | T096-T111 | 16 |
| 8 | Polish | T112-T122 | 11 |
| **Total** | | | **122** |

---

## MVP Checkpoints

### MVP 1: Basic Autonomous Loop
- Phase 1 + 2 + 3 (US1)
- Agents can run basic autonomous loops
- Test: Initialize framework, run iterations, check state

### MVP 2: Exit Conditions
- Add Phase 4 (US3)
- Agents can evaluate exit conditions
- Test: Run pytest via Code Interpreter, verify loop terminates

### MVP 3: Resilient
- Add Phase 5 (US2)
- Agents can recover from interruptions
- Test: Save checkpoint, simulate crash, recover

### MVP 4: Governed
- Add Phase 6 (US4)
- Iteration limits enforced by Policy
- Test: Set low limit, verify agent stops

### MVP 5: Observable
- Add Phase 7 (US5)
- Dashboard can query progress
- Test: Query Observability API, see progress

---

## Troubleshooting

### Worktree Issues

```bash
# List all worktrees
git worktree list

# Prune stale worktrees
git worktree prune

# Force remove a worktree
git worktree remove --force ../agent-orch-us2
```

### Ralph Issues

```bash
# Check ralph status
/tasks

# Cancel stuck ralph
/ralph-loop:cancel-ralph
```

### Merge Conflicts

If you get conflicts when merging worktrees:

1. The worktrees modified different files - should be rare if following the plan
2. If conflicts occur, resolve in main worktree
3. Run tests after merge: `pytest -m "not integration"`

---

## Speed Comparison

| Approach | Estimated Time | Notes |
|----------|----------------|-------|
| Sequential (all phases) | ~8-10 hours | Single developer |
| Parallel US1+US3 | ~4-5 hours | 2 sessions, then merge |
| Parallel US1+US3, US2+US4 | ~3-4 hours | 4 total sessions |
| Full parallel (3 worktrees) | ~2-3 hours | Maximum parallelism |

---

## Notes

- Always run tests after each phase: `pytest --cov=src -m "not integration"`
- Commit after completing each user story
- US5 (Dashboard) requires all other stories - cannot parallelize
- Polish phase should be done last in main worktree
