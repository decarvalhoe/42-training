# Module Prerequisites — Pedagogical Reasoning

## Source classification

The prerequisite relationships below are **inferred mapping**, not official 42 curriculum rules.
They reflect pedagogical logic based on skill dependencies observed in Linux/C/Python learning paths.

Official 42 projects define their own ordering. This graph is a preparation aid, not a substitute.

## Prerequisite graph

```
shell-basics (entry point)
├── shell-streams        — redirections need filesystem fluency first
├── shell-permissions    — ownership/chmod assume you can navigate and create files
├── c-basics             — compiling C requires terminal navigation
└── python-basics        — running scripts requires terminal navigation

shell-streams
├── shell-tooling        — find, pipes, man pages build on stream concepts
└── c-build-debug        — compiler output, piping to tools, reading error streams

shell-permissions
└── shell-tooling        — executable bit, PATH, script permissions

c-basics
├── c-memory             — pointers require solid syntax and control flow
└── c-build-debug        — you must write code before you can compile and debug it

c-memory + c-build-debug
└── c-libft-pushswap-bridge — library and algorithm work needs both memory and build skills

python-basics
└── python-oop-scripting — OOP and file handling build on language foundations

python-oop-scripting
└── ai-rag-agents        — RAG/agent work requires scripting, file I/O, and OOP patterns
```

## Design decisions

### Cross-track prerequisites

Three modules have cross-track prerequisites:

- **c-basics <- shell-basics**: You cannot compile and run C without navigating the filesystem and using the terminal. This is a practical dependency, not a conceptual one.
- **c-build-debug <- shell-streams**: Understanding compiler output, piping through grep, and reading stderr are stream skills applied to a C context.
- **python-basics <- shell-basics**: Running Python scripts, managing files, and using the terminal are prerequisites for any scripting work.

### Why not more cross-track links?

We avoid making the graph overly connected. For example, `ai-rag-agents` could depend on `shell-tooling` (for git and general Linux habits), but this would over-constrain the learner. The current graph enforces only what is pedagogically necessary — a learner blocked on a prerequisite should genuinely need that skill before proceeding.

### Transitive dependencies

The graph is intentionally shallow. `ai-rag-agents` depends on `python-oop-scripting`, which depends on `python-basics`, which depends on `shell-basics`. We do not list `python-basics` as a direct prerequisite of `ai-rag-agents` because the chain is already enforced transitively.
