# Mini-moulinette / Mini-norminette Catalog

- Status: representative community reference for 42 Lausanne preparation
- Review date: 2026-03-29

## Decision

- The public official checker identified for C style rules is `42school/norminette`.
- No public 42 Lausanne source found in this review names a campus-specific bundle called `mini-norminette` or `mini-moulinette`.
- For curriculum and quality-model purposes, the best public representative of that family is `k11q/mini-moulinette`.
- Therefore, the ambiguous label should be normalized as:
  `mini-moulinette-style community pre-check runner`

This is a governance decision, not proof that 42 Lausanne uses this exact repository internally.

## Authority Levels

| Resource | Tier | Authority | Why |
| --- | --- | --- | --- |
| `42school/norminette` | `official_42` | canonical for style | Official 42 repository for norm checks |
| `k11q/mini-moulinette` | `testers_and_tooling` | representative only | Public community pre-check runner that combines style, compile and functional checks |
| Claims about the exact Lausanne internal bundle | `inferred` | unverified | No public campus source identified in this pass |

## Coverage Snapshot

From the `mini-moulinette` README status table:

| Assignment | Coverage | Notes |
| --- | --- | --- |
| `C00` | `9/9` | covered |
| `C01` | `9/9` | covered |
| `C02` | `12/13` | one exercise missing |
| `C03` | `6/6` | covered |
| `C04` | `6/6` | covered |
| `C05` | `8/9` | some edge cases not fully covered |
| `C06` | `4/4` | covered |
| `C07` | `6/6` | some edge cases not fully covered |
| `C08` | `6/6` | mostly compilation checks |
| `C09` | `0/3` | WIP |
| `C10` | `0/4` | WIP |
| `C11` | `0/8` | WIP |
| `C12` | `0/18` | no public checks documented |
| `C13` | `0/8` | no public checks documented |

This makes the tool useful for Piscine-era C pre-checks, but not for the wider curriculum.

## Check Catalog

### 1. Style checks

- `mini-moulinette` calls `norminette` before running its own harnesses.
- If `norminette` is not installed, the script explicitly skips that phase.
- Conclusion: style validation is delegated to the official 42 checker and is not embedded in the mini runner itself.

### 2. Compilation checks

- The runner compiles a first harness with `cc -Wall -Werror -Wextra`.
- If that compilation fails, the exercise is marked as failed before functional checks.
- This covers basic compileability and warning discipline, but not sanitizer, linker, or multi-platform validation.

### 3. Functional checks

- Each exercise directory contains one or more C harnesses.
- The runner compiles each harness and expects the executable to return success.
- Sample harnesses check exact return values and exact stdout content.

Examples observed in public test files:

- `C05/ex00/ft_iterative_factorial.c`: checks normal values and a negative input edge case.
- `C00/ex00/ft_putchar.c`: checks stdout for regular characters plus newline, tab, null and `0xFF`.
- `C06/ex00/ft_print_program_name.c`: compiles a program, runs it with different argv shapes, and compares output.

### 4. Edge-case checks

- Edge cases exist, but coverage is uneven and exercise-specific.
- The README explicitly warns that the tool is not `100% accurate` and does not cover every moulinette case.
- The README also flags partial edge-case coverage for `C05` and `C07`.

### 5. Scoring behavior

- The README says the scoring follows the usual 42 practice where early failures can invalidate later credit.
- The shell runner tracks a `break_score` state and only increments marks while earlier exercises remain valid.
- Conclusion: the tool tries to approximate moulinette grading flow, not just run independent unit tests.

## What The Tool Does Not Authoritatively Cover

- Official project requirements from subject PDFs
- Campus-specific evaluator policy
- Peer-evaluation expectations
- Memory checks such as `valgrind`
- Broader post-Piscine projects like `libft`, `ft_printf`, `get_next_line`, `push_swap`
- Hidden moulinette tests and environment differences

## Platform And Maintenance Limits

- Assumes a local shell workflow and a home-directory install (`~/mini-moulinette`)
- Assumes `bash`, `cc`, and optionally `norminette`
- Only publicly documents checks for `C00` to `C13`
- Maintenance is community-driven, not campus-governed
- The repository itself warns that users should treat results with caution

## Recommended Modeling In This Repo

- Keep `norminette` as the official style-check reference.
- Model `mini-moulinette` as a `testers_and_tooling` verification aid.
- Do not claim that 42 Lausanne uses this exact bundle unless a campus source confirms it.
- When the product says `mini-norminette` or `mini-moulinette`, rewrite it internally as:
  `representative community pre-check bundle`

## Sources

- Official 42 norm checker: https://github.com/42school/norminette
- Representative community runner: https://github.com/k11q/mini-moulinette
- Runner entrypoint: https://github.com/k11q/mini-moulinette/blob/main/mini-moul.sh
- Runner core logic: https://github.com/k11q/mini-moulinette/blob/main/mini-moul/test.sh
- Sample functional tests:
  - https://github.com/k11q/mini-moulinette/blob/main/mini-moul/tests/C00/ex00/ft_putchar.c
  - https://github.com/k11q/mini-moulinette/blob/main/mini-moul/tests/C05/ex00/ft_iterative_factorial.c
  - https://github.com/k11q/mini-moulinette/blob/main/mini-moul/tests/C06/ex00/ft_print_program_name.c
