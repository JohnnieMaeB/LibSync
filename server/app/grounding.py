"""Policy answer grounding — every number in a policy answer must come from
the retrieved policy text (NEXT_FEATURES.md P0.1).

The live assistant has told patrons renewals are "up to 2" when the policy
says three. A number is the part of a policy answer a patron acts on, so this
check is deterministic, not a model's opinion: collect every quantity the
policy search returned this turn (plus anything in the patron's own question),
then flag any quantity in the reply that isn't among them. Equivalent forms
match: "three weeks" = "21 days", "$0.25" = "25 cents", "$5" = "$5.00".

It can't catch invented services or steps that carry no number; the prompt
rule in agent.py covers those, and the eval suite measures both.
"""

import re

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "hundred": 100,
}

# Numbers too generic to police ("one of our services", "no fees"). Never
# applied to money: "$1" is exactly the kind of number a patron acts on.
ALWAYS_ALLOWED = {0.0, 1.0}

# Unit conversions, so a correct answer in other units still matches:
# (unit pattern, factor to the family's base unit, family name).
UNITS = [
    (r"weeks?", 7, "days"),
    (r"days?", 1, "days"),
    (r"hours?|hrs?", 60, "minutes"),
    (r"minutes?|mins?", 1, "minutes"),
    (r"years?", 12, "months"),
    (r"months?", 1, "months"),
]

_WORD_ALTERNATION = "|".join(NUMBER_WORDS)
_QUANTITY = re.compile(
    r"(?P<money>\$\s?\d+(?:,\d{3})*(?:\.\d+)?)"
    r"|(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)"
    rf"|\b(?P<word>{_WORD_ALTERNATION})\b",
    re.IGNORECASE,
)
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
_AFTER = re.compile(r"[\s-]*(?P<unit>[A-Za-z%]+)")


def _value(match: re.Match) -> float:
    if match.group("money"):
        return float(match.group("money").lstrip("$").replace(",", "").strip())
    if match.group("number"):
        return float(match.group("number").replace(",", ""))
    return float(NUMBER_WORDS[match.group("word").lower()])


def _unit_after(text: str, end: int) -> str:
    following = _AFTER.match(text, end)
    return following.group("unit").lower() if following else ""


def quantities(text: str) -> list[tuple[float, str]]:
    """Every quantity in `text` with the word that follows it (its unit, if any).
    List markers ("1. ", "2) ") are skipped."""
    text = _LIST_MARKER.sub(" ", text)
    return [(_value(m), "$" if m.group("money") else _unit_after(text, m.end())) for m in _QUANTITY.finditer(text)]


def _equivalents(value: float, unit: str) -> set[float]:
    """The value plus its forms in related units ($0.25 also counts as 25
    cents; 3 weeks also counts as 21 days)."""
    found = {round(value, 4)}
    if unit == "$":
        found.add(round(value * 100, 4))  # dollars → cents
    if unit.startswith("cent"):
        found.add(round(value / 100, 4))  # cents → dollars
    for pattern, factor, _family in UNITS:
        if re.fullmatch(pattern, unit):
            base = value * factor
            for _other, other_factor, family in UNITS:
                if family == _family:
                    found.add(round(base / other_factor, 4))
    return found


def _is_money(unit: str) -> bool:
    return unit == "$" or unit.startswith("cent")


def allowed_values(sources: list[str]) -> tuple[set[float], set[float]]:
    """(every value in `sources`, only the money values). Money is kept apart
    so that "no one else" in a policy can't make "$1" look supported."""
    allowed: set[float] = set()
    money: set[float] = set()
    for text in sources:
        for value, unit in quantities(text):
            forms = _equivalents(value, unit)
            allowed |= forms
            if _is_money(unit):
                money |= forms
    return allowed, money


def unsupported_quantities(reply: str, sources: list[str]) -> list[str]:
    """Quantities in `reply` that none of `sources` supports, as written."""
    allowed, money = allowed_values(sources)
    problems = []
    cleaned = _LIST_MARKER.sub(" ", reply)
    for match in _QUANTITY.finditer(cleaned):
        value = _value(match)
        unit = "$" if match.group("money") else _unit_after(cleaned, match.end())
        permitted = money if _is_money(unit) else allowed | ALWAYS_ALLOWED
        if not (_equivalents(value, unit) & permitted):
            problems.append(match.group(0).strip())
    return problems
