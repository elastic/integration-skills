r"""grok_diff.py — differential tester for grok pattern changes in ingest pipelines.

Expands grok syntax into plain Python regexes so an OLD and NEW pattern set can be
diffed over a matrix of message shapes. Stdlib-only. Approximates the Oniguruma/joni
engine Elasticsearch embeds — sound for differential accept/reject analysis and
backtracking growth curves, NOT exact engine parity (see SKILL.md "Engine caveats").
Final validation is always `elastic-package test pipeline`.

Usage sketch (see __main__ for a runnable self-test):

    OLD = PatternSet(["^Source %{IP:src} - Dest %{IP:dst}$", ...], defs={...})
    NEW = PatternSet(["^%{PREFIX_OPT}Source %{IP:src} - Dest %{IP:dst}$"],
                     defs={"PREFIX_OPT": r"(?:\[[^\]]*\]%{SPACE})?"})
    diff(CASES, OLD, NEW)          # CASES = [(name, message_string), ...]
    time_growth(NEW, make_input)   # make_input(n) -> adversarial non-matching string
"""

import re
import time

# Common grok primitives, approximated. Add what your patterns need; take definitions
# from https://github.com/elastic/go-grok/tree/main/patterns (authoritative for ES 8.16+)
# or the legacy logstash-patterns-core bank. Keep additions NON-capturing.
BASE_PATTERNS = {
    "SPACE": r"\s*",
    "DATA": r".*?",
    "GREEDYDATA": r".*",
    "WORD": r"\b\w+\b",
    "NOTSPACE": r"\S+",
    "INT": r"(?:[+-]?(?:[0-9]+))",
    "NUMBER": r"(?:[+-]?(?:[0-9]+(?:\.[0-9]+)?)|\.[0-9]+)",
    "BASE10NUM": r"(?:[+-]?(?:[0-9]+(?:\.[0-9]+)?)|\.[0-9]+)",
    "IP": r"(?:(?:[0-9]{1,3}\.){3}[0-9]{1,3}|[0-9a-fA-F:]{2,})",  # IPv4 loose | IPv6 loose
    "IPV4": r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}",
    "HOSTNAME": r"\b(?:[0-9A-Za-z][0-9A-Za-z-]{0,62})(?:\.(?:[0-9A-Za-z][0-9A-Za-z-]{0,62}))*\.?\b",
    "USER": r"[a-zA-Z0-9._-]+",
    "USERNAME": r"[a-zA-Z0-9._-]+",
    "UUID": r"[A-Fa-f0-9]{8}-(?:[A-Fa-f0-9]{4}-){3}[A-Fa-f0-9]{12}",
    "TIMESTAMP_ISO8601": r"(?:\d{4})-(?:0[1-9]|1[0-2])-(?:[0-2][0-9]|3[01])[T ](?:2[0123]|[01]?[0-9]):?(?:[0-5][0-9])(?::?(?:[0-5][0-9]|60)(?:[:.,][0-9]+)?)?(?:Z|[+-](?:2[0123]|[01]?[0-9])(?::?[0-5][0-9]))?",
}

_GROK_REF = re.compile(r"%\{(\w+)(?::([^}:]*))?(?::[^}]*)?\}")  # %{NAME}, %{NAME:field}, %{NAME:field:type}
_ONIG_NAMED = re.compile(r"\(\?<([^>]+)>")                       # (?<field.with.dots>...)


class GrokError(KeyError):
    pass


def expand(pattern, defs=None, base=BASE_PATTERNS, _depth=0):
    """Expand grok references into a plain regex string.

    Field captures become Python named groups with sanitized names; a parallel
    name map is attached by PatternSet so captures report under the grok field name.
    """
    if _depth > 20:
        raise GrokError("recursion limit — circular pattern_definitions?")
    defs = defs or {}

    def rep(m):
        name, field = m.group(1), m.group(2)
        body = defs.get(name, base.get(name))
        if body is None:
            raise GrokError(f"unknown grok pattern %{{{name}}} — add it to defs or BASE_PATTERNS")
        body = expand(body, defs, base, _depth + 1)
        if field:
            return f"(?P<{_sanitize(field)}>{body})"
        return f"(?:{body})"

    out = _GROK_REF.sub(rep, pattern)
    # Oniguruma named groups may contain dots; rewrite to valid Python names.
    out = _ONIG_NAMED.sub(lambda m: f"(?P<{_sanitize(m.group(1))}>", out)
    return out


_name_registry = {}


def _sanitize(field):
    """Map a grok field name to a unique, valid Python group name."""
    base = re.sub(r"\W", "_", field)
    name, n = base, 1
    while name in _name_registry and _name_registry[name] != field:
        n += 1
        name = f"{base}_{n}"
    _name_registry[name] = field
    return name


def captures(match):
    """Named captures of a match, keyed by original grok field name, Nones dropped."""
    return {
        _name_registry.get(k, k): v
        for k, v in match.groupdict().items()
        if v is not None
    }


class PatternSet:
    """A grok processor's pattern list: first match wins."""

    def __init__(self, patterns, defs=None, label=""):
        self.label = label
        self.compiled = [re.compile(expand(p, defs)) for p in patterns]

    def match(self, text):
        for rx in self.compiled:
            m = rx.match(text)
            if m:
                return m
        return None


def diff(cases, old, new, show_captures=True):
    """Print an old-vs-new verdict table; return [(name, old_ok, new_ok, changed)]."""
    rows, width = [], max(len(n) for n, _ in cases) + 2
    print(f"{'case':<{width}} {'old':>4} {'new':>4}  notes")
    for name, msg in cases:
        om, nm = old.match(msg), new.match(msg)
        note = ""
        if om and not nm:
            note = "REGRESSION: old matched, new does not"
        elif nm and not om:
            note = "newly enabled — needs a fixture"
        elif om and nm and show_captures:
            oc, nc = captures(om), captures(nm)
            moved = {k for k in oc.keys() | nc.keys() if oc.get(k) != nc.get(k)}
            if moved:
                note = "CAPTURE CHANGE: " + ", ".join(
                    f"{k}: {oc.get(k)!r}->{nc.get(k)!r}" for k in sorted(moved))
            elif nc:
                note = " ".join(f"{k}={v!r}" for k, v in sorted(nc.items()))
        rows.append((name, bool(om), bool(nm), bool(note.startswith(("REGRESSION", "CAPTURE")))))
        print(f"{name:<{width}} {'YES' if om else 'no':>4} {'YES' if nm else 'NO!':>4}  {note}")
    return rows


def time_growth(pattern_set, make_input, sizes=(10, 20, 40, 80)):
    """Time matching of adversarial inputs of growing size. Judge the CURVE:
    linear is fine; superlinear means restructure the pattern."""
    print(f"{'n':>5} {'chars':>7} {'ms':>10}")
    for n in sizes:
        s = make_input(n)
        t = time.perf_counter()
        pattern_set.match(s)
        dt = (time.perf_counter() - t) * 1000
        print(f"{n:>5} {len(s):>7} {dt:>10.3f}")


if __name__ == "__main__":
    # Self-test: a refactor that collapses two patterns into one and, in doing so,
    # silently drops a shape the old catch-all accepted. Mirrors the class of bug
    # found in elastic/integrations#20710.
    OLD = PatternSet([
        "^Source %{IP:src} - SSLRelay %{IP:relay} - user %{WORD:user}$",
        "^%{DATA} Source %{IP:src} - user %{WORD:user}$",
    ], label="1.18.6")
    NEW = PatternSet([
        "^%{PREFIX_OPT}Source %{IP:src} - (?:SSLRelay %{IP:relay} - )?user %{WORD:user}$",
    ], defs={"PREFIX_OPT": r"(?:\[[^\]]*\]\s*)*"}, label="PR")

    CASES = [
        ("no prefix + relay",          "Source 10.0.0.1 - SSLRelay 10.0.0.2 - user bob"),
        ("bracket prefix, no relay",   "[TCP][CGP] Source 10.0.0.1 - user bob"),
        ("prefix + relay (was gap)",   "[TCP] Source 10.0.0.1 - SSLRelay 10.0.0.2 - user bob"),
        ("bare (was gap)",             "Source 10.0.0.1 - user bob"),
        ("non-bracket prefix",         "Client_ip 10.9.9.9 - Source 10.0.0.1 - user bob"),
    ]
    diff(CASES, OLD, NEW)
    print()
    time_growth(NEW, lambda n: "[" + "][".join(["X" * 20] * n) + "] Source not-an-ip")
