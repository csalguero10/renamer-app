import os
from .roman import format_number

def compute_new_name(original_filename: str, page_type: str, page_number, number_scheme="arabic", extra="", ghost=False):
    """Builds new filename keeping original prefix, adding type and number tokens.
    - page_number: int | False | None
    - extra: optional suffix like 'bis', 'a', 'v'
    - ghost: if True wrap number in []
    """
    base, ext = os.path.splitext(original_filename)
    suffix = page_type.strip()
    if page_number not in (None, False):
        token_num = format_number(int(page_number), number_scheme, ghost)
        suffix += f"_{token_num}{extra.strip()}"
    new_name = f"{base} {suffix}{ext}"
    return new_name
