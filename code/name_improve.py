import json
import os
import re

import wordninja

from extract_definition import MARKER

CORRECTIONS_PATH = os.path.join(os.path.dirname(__file__), "name_corrections.json")

with open(CORRECTIONS_PATH, "r", encoding="utf-8") as file:
    _corrections = json.load(file)
INPUT_CORRECTIONS = dict(_corrections["input_corrections"])
TOKEN_RENDER = {k.lower(): v for k, v in _corrections["token_render"].items()}
CORRECTION_KEYS = sorted(INPUT_CORRECTIONS, key=len, reverse=True)
CORRECTION_PATTERN = (
    re.compile("|".join(re.escape(k) for k in CORRECTION_KEYS)) if CORRECTION_KEYS else None
)

AGGREGATION_BOUND = re.compile(r"_\w\[")  # IfcComplexNumber_A[1:2] -> IfcComplexNumber

CAMEL_BOUNDARY = re.compile(
    r"(?<=[a-z])(?=[A-Z])"
    r"|(?<=[a-z])(?=[0-9])"
    r"|(?<=[A-Z][A-Z])(?=[0-9])"
    r"|(?<=[0-9])(?=[a-z])"
    r"|(?<=[0-9])(?=[A-Z][a-z])"
    r"|(?<=[0-9])(?=[A-Z][A-Z])"
    r"|(?<=[A-Z])(?=[A-Z][a-z])"
)

PLURAL_TAIL = re.compile(r"^[A-Z](s|es)$")
ACRONYM_PLURAL = re.compile(r"^[A-Z]{2,4}(s|es)$")


def _stage1_split(s):
    """Split underscores, whitespace, camelCase and digit boundaries into tokens."""
    s = re.sub(r"^Ifc", "", s)
    out = []
    for piece in re.split(r"[_\s]+", s):
        out.extend(t for t in CAMEL_BOUNDARY.split(piece) if t)
    return out


def _merge_acronym_plurals(tokens):
    """Glue an ALL-CAPS acronym to a following Ds/Ss-style plural fragment
    (['Messaging','I','Ds'] -> ['Messaging','IDs'])."""
    out, i = [], 0
    while i < len(tokens):
        cur, nxt = tokens[i], tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt and cur.isalpha() and cur.isupper() and 1 <= len(cur) <= 4 and PLURAL_TAIL.match(nxt):
            out.append(cur + nxt)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def _merge_acronyms(tokens):
    """Rejoin adjacent tokens whose concatenation is a known render key (CO + 2 -> CO2)."""
    out, i = [], 0
    while i < len(tokens):
        if i + 1 < len(tokens) and (tokens[i] + tokens[i + 1]).lower() in TOKEN_RENDER:
            out.append((tokens[i] + tokens[i + 1]).lower())
            i += 2
        else:
            out.append(tokens[i])
            i += 1
    return out


def _render(tokens):
    rendered = []
    for t in tokens:
        override = TOKEN_RENDER.get(t.lower())
        if override is not None:
            if override == override.lower() and not rendered:
                rendered.append(override[:1].upper() + override[1:])
            else:
                rendered.append(override)
        elif t.isdigit() or ACRONYM_PLURAL.match(t):
            rendered.append(t)
        else:
            rendered.append(t[:1].upper() + t[1:].lower())
    return " ".join(rendered)


def _process_span(s):
    tokens = []
    for tok in _stage1_split(s):
        if tok.isalpha() and tok.isupper() and len(tok) >= 5:
            tokens.extend(wordninja.split(tok))
        else:
            tokens.append(tok)
    return _render(_merge_acronyms(_merge_acronym_plurals(tokens)))


def _split_on_corrections(s):
    """Split s into ('process', span) and ('literal', final_form) parts around corrections."""
    if CORRECTION_PATTERN is None:
        return [("process", s)]
    parts, last = [], 0
    for m in CORRECTION_PATTERN.finditer(s):
        if m.start() > last:
            parts.append(("process", s[last : m.start()]))
        parts.append(("literal", INPUT_CORRECTIONS[m.group(0)]))
        last = m.end()
    if last < len(s):
        parts.append(("process", s[last:]))
    return parts


def name_improve(s):
    s = AGGREGATION_BOUND.split(s)[0]
    out = []
    for kind, val in _split_on_corrections(s):
        if kind == "literal":
            out.append(val)
        else:
            rendered = _process_span(val)
            if rendered:
                out.append(rendered)
    return " ".join(out).strip()


MULTIPLE_LINEBREAK_PATTERN = re.compile("\n+")
MULTIPLE_SPACE_PATTERN = re.compile(r"\s+")
HTML_TAG_PATTERN = re.compile("<.*?>")
CURLY_BRACKET_PATTERN = re.compile("{.*?}.*")  # also removes all text after curly brackets
FIGURE_PATTERN = re.compile("[^.,;]*(Figure|the figure)[^.,;]*")
LIST_PATTERN = re.compile(r"[^.,;]*:\s?")

replacements = [
    (re.compile(r"\*{2}"), " "),
    (re.compile(r":(?!\s)"), ": "),
    (re.compile(r"SELF\\"), ""),
    (re.compile(r"(?<!\.)\.\.(?!\.)"), "."),  # remove double dots but not triple (ellipsis)
    (MULTIPLE_LINEBREAK_PATTERN, "; "),
    (HTML_TAG_PATTERN, " "),
    (CURLY_BRACKET_PATTERN, " "),
    (FIGURE_PATTERN, ""),
    (LIST_PATTERN, ""),
    (MULTIPLE_SPACE_PATTERN, " "),
]


def remove_unwanted(s):
    for pat, subs in replacements:
        s = re.sub(pat, subs, s)
    return s


def clean(s):
    """format the text by removing unwanted characters."""
    s = re.sub(MULTIPLE_LINEBREAK_PATTERN, "; ", s)
    s = remove_unwanted(s)
    cleaned = "".join(
        ["", c][c.isalnum() or c in ":.,()-+ —=;α°_/!?$%@<>'\"\\*"] for c in s
    )
    p = re.compile('"')
    cleaned = re.sub(p, "'", cleaned).strip()
    return re.sub(MULTIPLE_SPACE_PATTERN, " ", cleaned).strip()


def definition_improve(s):
    return clean(s.split(MARKER.strip(), 1)[0].strip())


if __name__ == "__main__":
    checks = {
        "IfcActionRequest": "Action Request",
        "IfcPrestressingRail": "Prestressing Rail",
        "Railing": "Railing",
        "APPROACHSIGNAL": "Approach Signal",
        "BLADEPITCHANGLE": "Blade Pitch Angle",
        "TexCoordIndex_L[3:?]": "Tex Coord Index",
        "IfcComplexNumber_A[1:2]": "Complex Number",
        "GlobalId": "Global ID",
        "N20": "N2O",
        "ACTIVEBALISE": "Active Balise",
        "ASSIGNEE": "Assignee",
    }
    for src, want in checks.items():
        got = name_improve(src)
        assert got == want, f"{src!r}: got {got!r}, want {want!r}"
    print("name_improve self-check: OK")
