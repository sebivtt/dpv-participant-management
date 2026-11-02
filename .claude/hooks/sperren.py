"""Prüfschritt vor jedem Bash-Befehl in Claude Code (#233, `CLAUDE.md`, „Was die KI nie allein entscheidet oder tut“).

Claude Code ruft diese Datei vor jedem Bash-Befehl auf (`.claude/settings.json`, Hook `PreToolUse`)
und übergibt den Befehl als JSON auf der Standardeingabe. Exit 2 weist den Befehl ab; Claude Code
führt ihn dann nicht aus und zeigt der KI die Meldung. Exit 0 lässt ihn durch.

Abgewiesen wird, was allein Sebastian tut: Pull Request übernehmen, auf `main` oder mit Force
hochladen, `.env` lesen, das Label `geklärt` setzen. Geprüft wird nach Wirkung, nicht nach
Wortlaut: Die Befehlskette wird in ihre Teile zerlegt, und je Teil zählt, was Git oder `gh`
tatsächlich tun würden. `git push origin feature/main-menu` geht also durch, `git push origin
HEAD:refs/heads/main` nicht. Das ist ein Schutz vor Versehen und Gewohnheit, keiner gegen
absichtliches Verschleiern (Skript, Variable): Solche Befehle kann der Prüfschritt nicht sehen.

Was sich nicht sicher zerlegen lässt (offenes Anführungszeichen) und `git`, `gh` oder `.env`
enthält, wird abgewiesen, ebenso jeder Befehl, wenn im Prüfschritt selbst ein Fehler auftritt.
Nur Python-Standardbibliothek, damit der Prüfschritt ohne eingerichtete Umgebung läuft.
"""

import fnmatch
import json
import os
import re
import subprocess
import sys
import unicodedata

MESSAGE = "Gesperrt nach CLAUDE.md, ‚Was die KI nie allein entscheidet oder tut‘. Sebastian führt das selbst aus."
STILL_LOCKED = (
    "Pull Requests übernehmen, auf main oder mit Force hochladen, .env lesen und `geklärt` setzen "
    "bleiben gesperrt; das führt Sebastian selbst aus."
)
NAME_TARGET = "Bitte das Ziel ausdrücklich nennen: git push origin <zweig>."
SIMPLE = (
    "Bitte eine einfache Schreibweise verwenden: keine offenen Anführungszeichen, "
    "längere Texte als Datei (etwa --body-file oder -F body=@datei.md)."
)
LABEL = "geklärt"
PROTECTED_BRANCH = "main"
MENTIONS = re.compile(r"\bgit\b|\bgh\b|\.env")


class Blocked(Exception):
    """Ein Teil des Befehls ist gesperrt (`forbidden`) oder nicht sicher prüfbar."""

    def __init__(self, reason, hint=None):
        super().__init__(reason)
        self.reason = reason
        self.hint = hint

    def text(self):
        if self.hint is None:
            return f"{MESSAGE}\nGrund: {self.reason}."
        return f"Abgewiesen vom Prüfschritt .claude/hooks/sperren.py: {self.reason}. {self.hint}\n{STILL_LOCKED}"


class Unparsable(Exception):
    """Der Befehl lässt sich nicht sicher in Teile zerlegen."""


# --- Zerlegen ---------------------------------------------------------------------------------

SEPARATORS = ("&&", "||", "|&", ";;", "&", "|", ";", "(", ")")


class _Lexer:
    """Zerlegt einen Shell-Befehl in Teile (je Teil eine Wortliste), wie die Shell es täte.

    Anführungszeichen und `\\` werden aufgelöst. Der Inhalt von `$(…)` und `` `…` `` wird als
    eigene Teile mitgeprüft; der Text von Heredocs (`<<EOF … EOF`) ist nur Text und bleibt außen
    vor, damit etwa eine PR-Beschreibung, die `git push origin main` erwähnt, nicht sperrt.
    """

    def __init__(self, text, pos=0, in_substitution=False):
        self.text = text
        self.pos = pos
        self.in_substitution = in_substitution
        self.depth = 0
        self.segments = [[]]
        self.word = None
        self.heredocs = []
        self.nested_segments = []

    def run(self):
        while self.pos < len(self.text):
            if self._step():
                self._end_word()
                return self._result()
        if self.in_substitution:
            raise Unparsable("$( ohne schließende Klammer")
        self._end_word()
        return self._result()

    def _result(self):
        return [segment for segment in self.segments if segment]

    def _add(self, chars):
        self.word = (self.word or "") + chars

    def _end_word(self):
        if self.word is not None:
            self.segments[-1].append(self.word)
            self.word = None

    def _new_segment(self):
        self._end_word()
        self.segments.append([])

    def _step(self):
        """Verarbeitet ein Zeichen oder eine Zeichenfolge; True am Ende von `$(…)`."""
        text, pos = self.text, self.pos
        char = text[pos]
        if char == ")" and self.in_substitution and self.depth == 0:
            self.pos += 1
            return True
        if char in "\\'\"`$":
            self._quoted(char)
        elif char == "#" and self.word is None:
            end = text.find("\n", pos)
            self.pos = len(text) if end == -1 else end
        elif char in " \t":
            self._end_word()
            self.pos += 1
        elif char == "\n":
            self._new_segment()
            self.pos += 1
            self._read_heredocs()
        elif char in "<>":
            self._redirect()
        else:
            self._operator_or_char()
        return False

    def _quoted(self, char):
        text, pos = self.text, self.pos
        if char == "\\":
            following = text[pos + 1 : pos + 2]
            if following != "\n":
                self._add(following)
            self.pos += 2
        elif char == "'":
            end = text.find("'", pos + 1)
            if end == -1:
                raise Unparsable("offenes Anführungszeichen (')")
            self._add(text[pos + 1 : end])
            self.pos = end + 1
        elif char == '"':
            self._double_quoted()
        elif char == "`":
            self._backtick()
        elif text.startswith("$(", pos):
            self._substitution()
        else:
            self._add(char)
            self.pos += 1

    def _double_quoted(self):
        self.pos += 1
        self._add("")
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == '"':
                self.pos += 1
                return
            if char == "\\" and self.text[self.pos + 1 : self.pos + 2] in ('"', "\\", "$", "`"):
                self._add(self.text[self.pos + 1])
                self.pos += 2
            elif self.text.startswith("$(", self.pos):
                self._substitution()
            elif char == "`":
                self._backtick()
            else:
                self._add(char)
                self.pos += 1
        raise Unparsable('offenes Anführungszeichen (")')

    def _substitution(self):
        start = self.pos
        inner = _Lexer(self.text, self.pos + 2, in_substitution=True)
        self.nested_segments.extend(inner.run())
        self.nested_segments.extend(inner.nested_segments)
        self.pos = inner.pos
        self._add(self.text[start : self.pos])

    def _backtick(self):
        end = self.text.find("`", self.pos + 1)
        if end == -1:
            raise Unparsable("offenes Anführungszeichen (`)")
        inner = _Lexer(self.text[self.pos + 1 : end])
        self.nested_segments.extend(inner.run())
        self.nested_segments.extend(inner.nested_segments)
        self._add(self.text[self.pos : end + 1])
        self.pos = end + 1

    def _redirect(self):
        text = self.text
        if text.startswith("<<", self.pos) and not text.startswith("<<<", self.pos):
            self._heredoc_start()
            return
        self._end_word()
        while self.pos < len(text) and text[self.pos] in "<>&|":
            self.pos += 1

    def _heredoc_start(self):
        self._end_word()
        self.pos += 2
        strip_tabs = self.text.startswith("-", self.pos)
        if strip_tabs:
            self.pos += 1
        while self.pos < len(self.text) and self.text[self.pos] in " \t":
            self.pos += 1
        match = re.match(r"'([^']*)'|\"([^\"]*)\"|([^\s;&|<>()]+)", self.text[self.pos :])
        if not match:
            raise Unparsable("Heredoc ohne Endmarke")
        self.heredocs.append((next(group for group in match.groups() if group is not None), strip_tabs))
        self.pos += match.end()

    def _read_heredocs(self):
        """Überspringt die Zeilen der Heredocs, die in der vorigen Zeile begonnen haben."""
        for delimiter, strip_tabs in self.heredocs:
            while self.pos < len(self.text):
                end = self.text.find("\n", self.pos)
                end = len(self.text) if end == -1 else end
                line = self.text[self.pos : end]
                self.pos = min(end + 1, len(self.text))
                if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                    break
        self.heredocs = []

    def _operator_or_char(self):
        text = self.text
        if text.startswith("&>", self.pos):
            self._redirect()
            return
        for operator in SEPARATORS:
            if text.startswith(operator, self.pos):
                if operator == "(":
                    self.depth += 1
                elif operator == ")":
                    self.depth -= 1
                self._new_segment()
                self.pos += len(operator)
                return
        self._add(text[self.pos])
        self.pos += 1


def _lex(text):
    """Alle Teile eines Befehls, auch die aus `$(…)` und `` `…` ``."""
    lexer = _Lexer(text)
    segments = lexer.run()
    return segments + lexer.nested_segments



# --- Prüfen -----------------------------------------------------------------------------------

ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PREFIXES = {"env", "command", "exec", "nohup", "time", "sudo", "{", "!", "if", "then", "elif", "else", "do", "while", "until"}
SHELLS = {"bash", "sh", "zsh", "dash"}


def check(command, cwd):
    """Prüft einen ganzen Bash-Befehl; wirft `Blocked`, wenn ein Teil gesperrt ist."""
    try:
        segments = _lex(command)
    except Unparsable as error:
        if MENTIONS.search(command):
            raise Blocked(f"Befehl nicht sicher zerlegbar ({error})", SIMPLE) from error
        return
    for words in segments:
        _check_env(words)
        words = _strip_prefixes(words)
        if not words:
            continue
        program = words[0].rsplit("/", 1)[-1]
        if program == "cd" and len(words) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(words[1]))
        elif program == "git":
            _check_git(words, cwd)
        elif program == "gh":
            _check_gh(words, cwd)
        elif program in SHELLS or program == "eval":
            _check_shell(program, words, cwd)


def _strip_prefixes(words):
    """Lässt Variablenzuweisungen und Vorsätze wie `env` oder `if` vor dem eigentlichen Programm weg."""
    index = 0
    while index < len(words) and (ASSIGNMENT.match(words[index]) or words[index] in PREFIXES):
        index += 1
        while words[index - 1] == "env" and index < len(words) and words[index].startswith("-"):
            index += 1
    return words[index:]


def _check_shell(program, words, cwd):
    if program == "eval":
        check(" ".join(words[1:]), cwd)
        return
    for index, word in enumerate(words[1:-1], start=1):
        if word.startswith("-") and not word.startswith("--") and "c" in word:
            check(words[index + 1], cwd)
            return


def _normalized(text):
    return unicodedata.normalize("NFC", text).casefold()


def _check_env(words):
    """`.env` als Datei im Befehl ist gesperrt; `--env-file .env` (uv, Docker) liest sie nur für das Programm."""
    for index, word in enumerate(words):
        if word.startswith("--env-file") or (index and words[index - 1] == "--env-file"):
            continue
        name = word.rsplit("=", 1)[-1].rsplit("/", 1)[-1]
        # Ein Muster trifft in der Shell eine versteckte Datei nur, wenn es selbst mit „.“ beginnt.
        pattern = name.startswith(".") and any(char in name for char in "*?[")
        if name == ".env" or (pattern and fnmatch.fnmatchcase(".env", name)):
            raise Blocked(".env lesen")


# Git ---------------------------------------------------------------------------------------

GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
PUSH_OPTIONS_WITH_VALUE = {"--push-option", "--repo", "--receive-pack", "--exec", "--recurse-submodules"}
PUSH_FORBIDDEN = {"--mirror", "--all", "--branches", "--delete", "--prune"}


def _check_git(words, cwd):
    index = 1
    repo_dir = cwd
    while index < len(words) and words[index].startswith("-"):
        if words[index] in GIT_OPTIONS_WITH_VALUE:
            if words[index] == "-C" and index + 1 < len(words):
                repo_dir = os.path.join(repo_dir, os.path.expanduser(words[index + 1]))
            index += 1
        index += 1
    if index < len(words) and words[index] == "push":
        _check_push(words[index + 1 :], repo_dir)


def _check_push(args, repo_dir):
    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            positional += args[index + 1 :]
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in PUSH_FORBIDDEN or name.startswith("--force"):
                raise Blocked(f"git push {name}")
            if name in PUSH_OPTIONS_WITH_VALUE and "=" not in arg and name != "--recurse-submodules":
                index += 1
        elif arg.startswith("-") and len(arg) > 1:
            index += _check_short_push_options(arg)
        else:
            positional.append(arg)
        index += 1
    refspecs = positional[1:]
    if not refspecs:
        raise Blocked("git push ohne ausdrückliches Ziel (die eingestellte Zuordnung kann auf main zeigen)", NAME_TARGET)
    for refspec in refspecs:
        _check_refspec(refspec, repo_dir)


def _check_short_push_options(arg):
    """Prüft Kurzoptionen wie `-uf`; gibt 1 zurück, wenn der nächste Teil der Wert von `-o` ist."""
    for position, letter in enumerate(arg[1:], start=1):
        if letter in "fd":
            raise Blocked(f"git push -{letter}")
        if letter == "o":
            return 1 if position == len(arg) - 1 else 0
    return 0


def _check_refspec(refspec, repo_dir):
    if refspec.startswith("+"):
        raise Blocked(f"git push mit Force ({refspec})")
    source, colon, target = refspec.partition(":")
    if colon and not source:
        raise Blocked(f"git push löscht einen Zweig ({refspec})")
    target = target or source
    if target in ("HEAD", "@"):
        target = _current_branch(repo_dir)
    name = target.removeprefix("refs/").removeprefix("heads/")
    if name == PROTECTED_BRANCH or (any(char in name for char in "*?[") and fnmatch.fnmatchcase(PROTECTED_BRANCH, name)):
        raise Blocked(f"git push auf {PROTECTED_BRANCH} ({refspec})")


def _current_branch(repo_dir):
    try:
        result = subprocess.run(  # noqa: S603 -- fester Git-Aufruf, nur lesend
            ["git", "-C", repo_dir, "symbolic-ref", "--short", "-q", "HEAD"],  # noqa: S607 -- git aus dem PATH wie in der Sitzung
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Blocked("aktueller Zweig für HEAD nicht ermittelbar", NAME_TARGET) from error
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch:
        raise Blocked("aktueller Zweig für HEAD nicht ermittelbar", NAME_TARGET)
    return branch


# gh ----------------------------------------------------------------------------------------

LABEL_OPTIONS = {"-l", "--label", "--add-label"}
API_OPTIONS_WITH_VALUE = {
    "-X", "--method", "-f", "--raw-field", "-F", "--field", "-H", "--header", "--input",
    "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview",
}
API_SHORT_WITH_VALUE = {"-X", "-f", "-F", "-H", "-q", "-t", "-p"}
MERGE_PATH = re.compile(r"(^|/)pulls/[^/]+/merge/?$")
MUTATION = re.compile(r"\bmutation\b", re.IGNORECASE)


def _positionals(args):
    """Teile ohne Optionen; der Wert von `-R`/`--repo` zählt nicht mit."""
    result = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in ("-R", "--repo"):
            skip = True
        elif not arg.startswith("-"):
            result.append(arg)
    return result


def _check_gh(words, cwd):
    args = words[1:]
    command = _positionals(args)[:2]
    if command[:1] == ["api"]:
        _check_api(args[args.index("api") + 1 :], cwd)
    elif command == ["pr", "merge"]:
        raise Blocked("gh pr merge")
    elif len(command) == 2 and command[0] in ("issue", "pr") and command[1] in ("create", "new", "edit"):
        _check_label_options(args)


def _check_label_options(args):
    for index, arg in enumerate(args):
        name, value = _option(arg, args[index + 1 : index + 2])
        if name in LABEL_OPTIONS and value is not None and LABEL in _normalized(value):
            raise Blocked(f"Label {LABEL} setzen ({arg})")


def _option(arg, following):
    """Name und Wert einer Option in den Formen `--name wert`, `--name=wert`, `-n wert` und `-nwert`."""
    if arg.startswith("--"):
        name, equals, value = arg.partition("=")
        return name, value if equals else (following[0] if following else None)
    if arg.startswith("-") and len(arg) > 2:
        return arg[:2], arg[2:]
    if arg.startswith("-"):
        return arg, following[0] if following else None
    return None, None


def _check_api(args, cwd):
    endpoint, method, fields, inputs = _parse_api(args)
    path = re.sub(r"^https?://[^/]+/", "", endpoint or "").lstrip("/").split("?", 1)[0]
    if MERGE_PATH.search(path) and (method or "").upper() != "GET":
        raise Blocked("Pull Request über gh api übernehmen")
    for name, value, from_file in fields:
        relevant = path == "graphql" or name.startswith("labels")
        if relevant and from_file:
            value = _read(value, cwd)
        if path == "graphql" and MUTATION.search(value):
            raise Blocked("gh api graphql mit mutation")
        if name.startswith("labels") and LABEL in _normalized(value):
            raise Blocked(f"Label {LABEL} über gh api setzen")
    for source in inputs:
        _check_api_input(source, path, cwd)


def _parse_api(args):
    endpoint, method, fields, inputs = None, None, [], []
    index = 0
    while index < len(args):
        arg = args[index]
        name, value = _option(arg, args[index + 1 : index + 2])
        if name is None:
            endpoint = endpoint or arg
        elif name in API_OPTIONS_WITH_VALUE and value is not None:
            if name in ("-X", "--method"):
                method = value
            elif name in ("-f", "--raw-field", "-F", "--field"):
                key, _, field_value = value.partition("=")
                fields.append((key, field_value, name in ("-F", "--field") and field_value.startswith("@")))
            elif name == "--input":
                inputs.append(value)
            if "=" not in arg[2:] and not (name in API_SHORT_WITH_VALUE and len(arg) > 2):
                index += 1
        index += 1
    return endpoint, method, fields, inputs


def _read(source, cwd):
    """Inhalt einer Datei, die `gh` mit `@datei` oder `--input` liest; nicht lesbar heißt nicht prüfbar."""
    source = source.removeprefix("@")
    if source == "-":
        raise Blocked("gh api liest von der Standardeingabe, Inhalt nicht prüfbar", SIMPLE)
    try:
        with open(os.path.join(cwd, os.path.expanduser(source)), encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        raise Blocked(f"Datei {source} für gh api nicht lesbar, Inhalt nicht prüfbar", SIMPLE) from error


def _check_api_input(source, path, cwd):
    content = _read(source, cwd)
    if path == "graphql" and MUTATION.search(content):
        raise Blocked("gh api graphql mit mutation")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return
    if _labels_in(data):
        raise Blocked(f"Label {LABEL} über gh api setzen")


def _labels_in(data):
    if isinstance(data, dict):
        return any(
            (str(key).startswith("labels") and LABEL in _normalized(json.dumps(value, ensure_ascii=False)))
            or _labels_in(value)
            for key, value in data.items()
        )
    if isinstance(data, list):
        return any(_labels_in(item) for item in data)
    return False


# --- Aufruf durch Claude Code -----------------------------------------------------------------


def main():
    """Liest den Aufruf von Claude Code und gibt 0 (durchlassen) oder 2 (abweisen) zurück."""
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") != "Bash":
            return 0
        check(data["tool_input"]["command"], data.get("cwd") or os.getcwd())
    except Blocked as blocked:
        sys.stderr.write(blocked.text() + "\n")
        return 2
    # Sicherer Stillstand: Ein Fehler im Prüfschritt darf keinen gesperrten Befehl durchlassen.
    # Deshalb hier bewusst jeder Fehler, und der Befehl wird abgewiesen statt ausgeführt.
    except Exception as error:
        sys.stderr.write(
            f"Abgewiesen: Fehler im Prüfschritt .claude/hooks/sperren.py ({type(error).__name__}). {SIMPLE}\n{STILL_LOCKED}\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
