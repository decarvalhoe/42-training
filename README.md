# 42 Training

Linux-first training workspace for preparing 42 Lausanne.

This repository now combines two needs in a single project:

- a personal progression tracker for bash, Git, Vim and C
- a Linux-only mentor toolkit that can guide the work without taking it over

The supported runtime is Ubuntu on bare metal or Ubuntu inside WSL2. The host
OS can be Windows, but all real commands and scripts run on Linux.

## Principles

- One repository only
- One canonical path: `~/42-training`
- Linux-only workflow
- The mentor helps with questions, hints and checks, not full solutions by default
- The source of truth for progression is `progression.json`

## Quick Start

```bash
git clone https://github.com/decarvalhoe/42-training.git ~/42-training
cd ~/42-training
chmod +x save_progress.sh scripts/*.sh
./scripts/bootstrap_ubuntu_42.sh
./scripts/doctor.sh
./scripts/print_session_state.sh
```

To start a mentor-enabled work session from the repository root:

```bash
./scripts/start_42_mentor_env.sh .
```

Then attach the tmux sessions:

```bash
tmux attach -t learn42
tmux attach -t mentor42
```

## Repository Layout

```text
42-training/
|-- README.md
|-- progression.json
|-- REPRENDRE_SESSION.md
|-- save_progress.sh
|-- hello.txt
|-- test.txt
|-- prompts/
|   `-- mentor_system_prompt.txt
`-- scripts/
    |-- ask_mentor.sh
    |-- bootstrap_ubuntu_42.sh
    |-- doctor.sh
    |-- e2e_smoke_test.sh
    |-- print_session_state.sh
    |-- setup_github_auth.sh
    |-- start_42_mentor_env.sh
    |-- teardown_mentor_env.sh
    |-- update_progress.sh
    `-- watch_mentor.sh
```

## Daily Workflow

1. Open Ubuntu or WSL Ubuntu.
2. `cd ~/42-training`
3. `./scripts/doctor.sh`
4. `./scripts/print_session_state.sh`
5. Work in the `learn42` tmux session.
6. Ask for guidance only when needed:
   `m "je bloque sur ft_strlen"`
7. Update the progression file with the helper:
   `./scripts/update_progress.sh --step "2.5 - Supprimer fichier" --next-command "rm test.txt"`
8. Save the session:
   `./save_progress.sh`
9. Stop the sessions cleanly when needed:
   `./scripts/teardown_mentor_env.sh`
10. Commit and push with normal Git flow:
   `git add . && git commit -m "Progression du jour" && git push`

## Progression

Current progression lives in [`progression.json`](progression.json).
Do not duplicate the exact current step in multiple files. Read it from JSON and
use [`scripts/print_session_state.sh`](scripts/print_session_state.sh) for a
quick summary.

## Mentor Mode

The mentor toolkit comes from the local `42-remote-mentor-kit` and has been
merged here so the repository stays self-contained.

What it adds:

- `tmux` sessions for work, build and tests
- a dedicated mentor session running Claude on Linux
- quick feedback with terminal capture
- periodic watch mode
- an end-to-end smoke test for pedagogy rules

The mentor contract is strict:

- no full solution by default
- one useful question
- one hint
- one next action
- answers in French

See [`prompts/mentor_system_prompt.txt`](prompts/mentor_system_prompt.txt).

## GitHub Auth

Use GitHub CLI or SSH, but do not inject tokens into the remote URL.

Helper:

```bash
./scripts/setup_github_auth.sh
```

Pushes should remain standard:

```bash
git push
```

## Useful Commands

```bash
./scripts/bootstrap_ubuntu_42.sh
./scripts/doctor.sh
./scripts/print_session_state.sh
./scripts/start_42_mentor_env.sh .
./scripts/update_progress.sh --help
./scripts/teardown_mentor_env.sh
./scripts/watch_mentor.sh
./scripts/e2e_smoke_test.sh
./save_progress.sh
```

## License

MIT
