#!/usr/bin/env bash
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${HOME}/42-e2e-test"
LEARN_SESSION="learn42"
MENTOR_SESSION="mentor42"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAILURES=$((FAILURES+1)); }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

FAILURES=0

cleanup() {
  "${KIT_ROOT}/scripts/teardown_mentor_env.sh" --purge-tmp --quiet || true
  rm -rf "${WORK_ROOT}"
}

trap cleanup EXIT

info "Cleaning previous test state"
"${KIT_ROOT}/scripts/teardown_mentor_env.sh" --purge-tmp --quiet || true
mkdir -p "${WORK_ROOT}"

info "Creating test project with deliberate bug"
cat > "${WORK_ROOT}/ft_strlen.c" <<'CEOF'
#include <unistd.h>

int	ft_strlen(char *s)
{
	int	i;

	while (s[i] != '\0')
	{
		i++;
	}
	return (i);
}
CEOF

cat > "${WORK_ROOT}/main.c" <<'CEOF'
#include <stdio.h>

int	ft_strlen(char *s);

int	main(void)
{
	printf("%d\n", ft_strlen("hello"));
	printf("%d\n", ft_strlen(""));
	printf("%d\n", ft_strlen("42 school"));
	return (0);
}
CEOF

cat > "${WORK_ROOT}/Makefile" <<'MEOF'
NAME = test_strlen
CC = cc
CFLAGS = -Wall -Wextra -Werror

SRCS = ft_strlen.c main.c

all: $(NAME)

$(NAME): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(NAME)
MEOF

info "Creating tmux sessions"
export LEARN_SESSION MENTOR_SESSION
"${KIT_ROOT}/scripts/start_42_mentor_env.sh" "${WORK_ROOT}"

tmux has-session -t "${LEARN_SESSION}" 2>/dev/null && pass "learn42 session created" || fail "learn42 session missing"
tmux has-session -t "${MENTOR_SESSION}" 2>/dev/null && pass "mentor42 session created" || fail "mentor42 session missing"

info "Simulating student build"
tmux send-keys -t "${LEARN_SESSION}:build" "cd ${WORK_ROOT} && make 2>&1" C-m
sleep 3

info "Calling mentor quick mode"
MENTOR_RESPONSE="$(
  "${KIT_ROOT}/scripts/ask_mentor.sh" \
    --file ft_strlen.c \
    "J'ai une erreur de compilation ou un comportement bizarre. Aide-moi a comprendre sans donner la solution." \
  2>&1
)" || true

mkdir -p "${HOME}/.42-mentor/tmp"
printf '%s\n' "${MENTOR_RESPONSE}" > "${HOME}/.42-mentor/tmp/e2e-response.txt"

[[ -n "${MENTOR_RESPONSE}" && "${#MENTOR_RESPONSE}" -gt 50 ]] && pass "mentor responded" || fail "mentor response too short"
echo "${MENTOR_RESPONSE}" | grep -qiE "initiali|variable i|valeur.*i" && pass "bug identified" || fail "bug not identified"
echo "${MENTOR_RESPONSE}" | grep -qE "\?" && pass "question present" || fail "no question found"
if echo "${MENTOR_RESPONSE}" | grep -qE "i\s*=\s*0\s*;.*while.*s\[i\].*i\+\+.*return"; then
  fail "full solution leaked"
else
  pass "no full solution leaked"
fi

echo ""
if [[ ${FAILURES} -eq 0 ]]; then
  echo -e "${GREEN}All tests passed.${NC}"
else
  echo -e "${RED}${FAILURES} test(s) failed.${NC}"
fi

exit "${FAILURES}"
