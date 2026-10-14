"""Common English nicknames → canonical first name (03 §M2). Pure data.

Only unambiguous nicknames are listed. `al` (albert / alan / alexander), `chris` (christopher /
christine) or names that are also given names on their own (`liam`, `drew`) would merge different
people, so they are left out and stay as written.
"""

from types import MappingProxyType

_CANONICAL_TO_NICKNAMES: dict[str, tuple[str, ...]] = {
    "abigail": ("abby", "abbie"),
    "andrew": ("andy",),
    "anthony": ("tony",),
    "barbara": ("barb", "babs"),
    "benjamin": ("ben", "benny", "benji"),
    "catherine": ("cathy", "kate", "katie"),
    "charles": ("charlie", "chuck"),
    "daniel": ("dan", "danny"),
    "david": ("dave", "davey"),
    "deborah": ("deb", "debbie"),
    "donald": ("don", "donnie"),
    "edward": ("ed", "eddie", "ned"),
    "elizabeth": ("liz", "lizzie", "beth", "betty", "eliza"),
    "gregory": ("greg",),
    "james": ("jim", "jimmy", "jamie"),
    "jennifer": ("jen", "jenny"),
    "jessica": ("jess", "jessie"),
    "john": ("johnny", "jack"),
    "jonathan": ("jon", "jonny"),
    "joseph": ("joe", "joey"),
    "joshua": ("josh",),
    "kenneth": ("ken", "kenny"),
    "kimberly": ("kim",),
    "lawrence": ("larry",),
    "margaret": ("maggie", "meg", "peggy"),
    "matthew": ("matt",),
    "michael": ("mike", "mikey", "mick"),
    "nathaniel": ("nate", "nat"),
    "nicholas": ("nick", "nicky"),
    "patricia": ("pat", "patty", "trish"),
    "peter": ("pete",),
    "rebecca": ("becky", "becca"),
    "richard": ("rick", "ricky", "dick", "rich"),
    "robert": ("rob", "bob", "bobby", "robbie"),
    "ronald": ("ron", "ronnie"),
    "samuel": ("sam", "sammy"),
    "stephen": ("steve", "stevie"),
    "susan": ("sue", "susie"),
    "theodore": ("ted", "teddy", "theo"),
    "thomas": ("tom", "tommy"),
    "timothy": ("tim", "timmy"),
    "victoria": ("vicky", "tori"),
    "william": ("will", "bill", "billy", "willy"),
    "zachary": ("zach", "zack"),
}

NICKNAMES: MappingProxyType[str, str] = MappingProxyType(
    {
        nickname: canonical
        for canonical, nicknames in _CANONICAL_TO_NICKNAMES.items()
        for nickname in nicknames
    }
)


def expand_nickname(token: str) -> str:
    """The canonical first name for a lower-case nickname token; other tokens unchanged."""
    return NICKNAMES.get(token, token)


def nicknames_for(canonical: str) -> tuple[str, ...]:
    """Nicknames of a canonical first name (for the simulator's nickname noise)."""
    return _CANONICAL_TO_NICKNAMES.get(canonical, ())
