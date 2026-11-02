"""Tests für den Prüfschritt `.claude/hooks/sperren.py` (#233, Paket P-01 der Projektprüfung).

Claude Code ruft den Prüfschritt vor jedem Bash-Befehl auf und übergibt den Befehl als JSON.
Exit 2 heißt: abgewiesen, Claude Code führt den Befehl nicht aus. Gesperrt sind nur die Handlungen,
die allein Sebastian ausführt: Pull Request übernehmen, auf `main` oder mit Force hochladen,
`.env` lesen, das Label `geklärt` setzen. Alles andere muss weiter gehen, vor allem den eigenen
Zweig hochladen, Pull Requests und Issues anlegen und `geklärt` wieder entfernen.

Die Tests rufen den Prüfschritt so auf wie Claude Code: als eigenes Programm mit JSON auf der
Standardeingabe. Sie führen keinen der Befehle aus.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
HOOK = BASE_DIR / ".claude" / "hooks" / "sperren.py"
BLOCKED = 2
MESSAGE = "Gesperrt nach CLAUDE.md, ‚Was die KI nie allein entscheidet oder tut‘. Sebastian führt das selbst aus."

PR_BODY_HEREDOC = """gh pr create --title "Sperren (#233)" --body "$(cat <<'EOF'
Kein "git push origin main" und kein `gh pr merge`, das Label geklärt setzt Sebastian.
Ein offenes ' Anführungszeichen und eine Klammer ) stören hier nicht.
EOF
)\""""


def _run(payload, cwd=None):
    return subprocess.run(  # noqa: S603 -- fester Aufruf des eigenen Prüfschritts mit erfundenen Befehlen
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd or BASE_DIR,
        timeout=30,
        check=False,
    )


def _check(command, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd or BASE_DIR)}
    return _run(json.dumps(payload), cwd)


def _repo_on_branch(path, branch):
    """Leeres Git-Repo, dessen aktueller Zweig `branch` ist (für `git push origin HEAD`)."""
    subprocess.run(["git", "init", "-q", "-b", branch, str(path)], check=True)  # noqa: S603, S607 -- erfundenes Wegwerf-Repo
    return path


# --- Sperrfälle -------------------------------------------------------------------------------

BLOCKED_MERGE = [
    "gh pr merge 12 --merge",
    "gh -R sebivtt/x pr merge 12",
    "cd x && gh pr merge 12",
    "gh pr merge 12 --squash --delete-branch; echo fertig",
    "gh api -X PUT repos/sebivtt/x/pulls/12/merge",
    "gh api repos/sebivtt/x/pulls/12/merge -f merge_method=squash",
    "gh api repos/sebivtt/x/pulls/12/merge",
    "gh api --method=PUT https://api.github.com/repos/sebivtt/x/pulls/12/merge",
    "gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"X\"}) { clientMutationId } }'",
    "gh api graphql -F query='mutation($id: ID!) { addLabelsToLabelable(input: {labelableId: $id}) { clientMutationId } }'",
]

BLOCKED_PUSH = [
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin HEAD:refs/heads/main",
    "git push origin x:main",
    "git push origin verbesserung/a main",
    "git -C /pfad push origin main",
    "git -c color.ui=never push origin main",
    "git push",
    "git push origin",
    "git push -u origin",
    "git push --force origin verbesserung/x",
    "git push -f",
    "git push -uf origin verbesserung/x",
    "git push --force-with-lease origin verbesserung/x",
    "git push --force-with-lease=verbesserung/x origin verbesserung/x",
    "git push origin +HEAD:refs/heads/verbesserung/x",
    "git push origin +verbesserung/x",
    "git push --all origin",
    "git push --branches origin",
    "git push --mirror origin",
    "git push origin --delete verbesserung/x",
    "git push origin -d verbesserung/x",
    "git push origin :verbesserung/x",
    "git push --prune origin 'refs/heads/*:refs/heads/*'",
    "git push origin 'refs/heads/*:refs/heads/*'",
    "git add . && git commit -m 'Stand' && git push origin main",
    "git push origin main 2>&1 | tail -n 5",
    "bash -c 'git push origin main'",
    "git push origin \"verbesserung/x",
]

BLOCKED_LABEL = [
    "gh issue edit 5 --add-label geklärt",
    "gh issue edit 5 --add-label=P1,geklärt",
    "gh issue edit 5 --add-label P1 --add-label geklärt",
    "gh issue create -t T -l geklärt",
    "gh issue create -t T --label=geklärt -b B",
    "gh issue create -t T -l enhancement,geklärt -b B",
    "gh pr edit 3 --add-label geklärt",
    "gh -R sebivtt/x issue edit 5 --add-label geklärt",
    "gh api repos/sebivtt/x/issues/5/labels -f 'labels[]=geklärt'",
    "gh api repos/sebivtt/x/issues -f title=T -f 'labels[]=geklärt'",
    "gh api -X PATCH repos/sebivtt/x/issues/5 -f 'labels[]=geklärt'",
    "gh api repos/sebivtt/x/issues/5/labels --raw-field 'labels[]=geklärt'",
    # „geklärt“ zerlegt geschrieben (a und Trema als zwei Zeichen), wie es manche Eingaben liefern
    "gh issue edit 5 --add-label geklärt",
]

BLOCKED_ENV = [
    "cat .env",
    "head dev/.env",
    "cat /Users/erfunden/projekt/.env",
    "grep KEY .env",
    "less < .env",
    "cat .en*",
    "cat .*",
]


@pytest.mark.parametrize("command", BLOCKED_MERGE + BLOCKED_PUSH + BLOCKED_LABEL + BLOCKED_ENV)
def test_gesperrte_handlung_wird_abgewiesen(command):
    result = _check(command)

    assert result.returncode == BLOCKED, (command, result.stderr)
    assert "Gesperrt nach CLAUDE.md" in result.stderr or "Abgewiesen" in result.stderr


@pytest.mark.parametrize("command", ["gh pr merge 12 --merge", "git push origin main", "cat .env"])
def test_meldung_nennt_die_regel_und_dass_sebastian_selbst_ausfuehrt(command):
    assert MESSAGE in _check(command).stderr


def test_push_ohne_ziel_nennt_die_einfache_schreibweise():
    stderr = _check("git push").stderr

    assert "git push origin <zweig>" in stderr


def test_push_von_head_auf_zweig_main_wird_abgewiesen(tmp_path):
    repo = _repo_on_branch(tmp_path / "repo", "main")

    for command in ["git push origin HEAD", f"git -C {repo} push origin HEAD", f"cd {repo} && git push -u origin HEAD"]:
        result = _check(command, cwd=repo if command == "git push origin HEAD" else None)

        assert result.returncode == BLOCKED, command
        assert MESSAGE in result.stderr, command


def test_offenes_anfuehrungszeichen_bei_gh_wird_abgewiesen():
    result = _check("gh issue edit 5 --add-label 'P1")

    assert result.returncode == BLOCKED
    assert "einfache" in result.stderr


def test_label_aus_json_datei_wird_geprueft(tmp_path):
    (tmp_path / "geklaert.json").write_text(json.dumps({"labels": ["geklärt"]}), encoding="utf-8")
    (tmp_path / "anders.json").write_text(json.dumps({"labels": ["P2"], "body": "geklärt"}), encoding="utf-8")

    assert _check("gh api repos/sebivtt/x/issues/5 -X PATCH --input geklaert.json", cwd=tmp_path).returncode == BLOCKED
    assert _check("gh api repos/sebivtt/x/issues/5 -X PATCH --input anders.json", cwd=tmp_path).returncode == 0


def test_fehlerhafte_eingabe_wird_abgewiesen():
    result = _run("kein JSON")

    assert result.returncode == BLOCKED
    assert "Prüfschritt" in result.stderr


# --- Gegenfälle -------------------------------------------------------------------------------

ALLOWED = [
    "git push origin verbesserung/P-01-sperren",
    "git push -u origin claude/x",
    "git -C /pfad push -u origin verbesserung/x",
    "git push origin feature/main-menu",
    "git push origin maintenance",
    "git push origin main:refs/heads/verbesserung/kopie",
    "git push --tags origin verbesserung/x",
    "git add . && git commit -m 'Sperren (#233)' && git push -u origin verbesserung/P-01-sperren",
    "gh pr create --title T --body-file pr.md --base main",
    PR_BODY_HEREDOC,
    "gh pr view 12",
    "gh pr checks 12",
    "gh pr view 12 --json mergeable,mergeStateStatus",
    "gh run rerun 123456 --failed",
    "gh issue create -l enhancement -l P1 -t T -b B",
    "gh issue create -t 'Ist das geklärt?' -b 'Das Label geklärt setzt Sebastian.'",
    "gh api repos/sebivtt/x/issues -f title=T -F body=@datei.md -f 'labels[]=P2'",
    "gh issue edit 5 --remove-label geklärt",
    "gh issue edit 5 --add-label P1 --remove-label geklärt",
    "gh api -X DELETE repos/sebivtt/x/issues/5/labels/geklärt",
    "gh api repos/sebivtt/x/issues/5/comments -f body='Ist geklärt'",
    "gh api repos/sebivtt/x/issues/5/labels --jq '.[].name'",
    "gh api -X GET repos/sebivtt/x/pulls/12/merge",
    "gh api repos/sebivtt/x/pulls/12 --jq .merged",
    "gh api graphql -f query='query { repository(owner: \"sebivtt\", name: \"x\") { id } }'",
    "gh api repos/sebivtt/x/issues/5/sub_issues -F sub_issue_id=1",
    "gh label list",
    "cat .env.example",
    "cat testumgebung/.env.example",
    "./pruefen.sh",
    "uv run --locked --env-file .env pytest tests/test_sperren.py -q",
    "uv run --locked --env-file=.env python manage.py check",
    "ls -a",
    # Ein Muster ohne Punkt am Anfang trifft in der Shell keine versteckte Datei wie .env.
    "ls tests/*",
    "cat * | wc -l",
    "[ -f README.md ] && echo da",
    "echo \"ein offenes Anführungszeichen",
    "git status && git log --oneline -3",
    "git commit -m 'Kein git push origin main, kein gh pr merge'",
]


@pytest.mark.parametrize("command", ALLOWED)
def test_erlaubter_befehl_geht_weiter(command):
    result = _check(command)

    assert result.returncode == 0, (command, result.stderr)


def test_push_von_head_auf_eigenem_zweig_geht_weiter(tmp_path):
    repo = _repo_on_branch(tmp_path / "repo", "verbesserung/x")

    assert _check("git push origin HEAD", cwd=repo).returncode == 0
    assert _check(f"git -C {repo} push -u origin HEAD").returncode == 0


def test_andere_werkzeuge_als_bash_laesst_der_pruefschritt_unberuehrt():
    payload = {"tool_name": "Read", "tool_input": {"file_path": ".env.example"}, "cwd": str(BASE_DIR)}

    assert _run(json.dumps(payload)).returncode == 0
