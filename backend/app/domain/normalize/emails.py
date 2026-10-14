"""Email addresses (03 §M2, FR-NRM-002)."""

from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

# Providers that ignore dots and `+tag` in the local part.
_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


@dataclass(frozen=True, slots=True)
class NormalizedEmail:
    """`display` keeps dots and `+tag` (shown to users); `canonical` is used for matching."""

    display: str
    canonical: str
    domain: str

    @property
    def local_part(self) -> str:
        return self.canonical.rsplit("@", 1)[0]


def normalize_email(value: str | None) -> NormalizedEmail | None:
    """Lower-case and validate; `None` when missing or not a valid address.

    `John.Smith+crm@Gmail.com` → display `john.smith+crm@gmail.com`, canonical
    `johnsmith@gmail.com`. Syntax only: no DNS lookup, so the function stays pure.
    """
    if value is None or not value.strip():
        return None
    try:
        result = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError:
        return None
    local, domain = result.local_part.casefold(), result.domain.casefold()
    display = f"{local}@{domain}"
    if domain in _GMAIL_DOMAINS:
        stripped = local.split("+", 1)[0].replace(".", "")
        # `+tag@gmail.com` has no address left to match on; keep it as written.
        local, domain = (stripped or local), "gmail.com"
    return NormalizedEmail(display=display, canonical=f"{local}@{domain}", domain=domain)
