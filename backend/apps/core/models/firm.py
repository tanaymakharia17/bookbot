import uuid

from django.db import models


class CpaFirm(models.Model):
    """Top-level tenant: a CPA firm."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["firm_name"]
        verbose_name = "CPA firm"
        verbose_name_plural = "CPA firms"

    def __str__(self) -> str:
        return self.firm_name