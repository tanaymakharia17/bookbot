"""Core domain services."""
from django.conf import settings

from .models import CpaFirm


def get_default_firm() -> CpaFirm:
    """Return the default CPA firm, creating it on first use.

    Auth is not implemented yet, so all data is scoped to a single firm.
    """
    firm, _ = CpaFirm.objects.get_or_create(firm_name=settings.DEFAULT_FIRM_NAME)
    return firm