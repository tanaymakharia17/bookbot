import uuid

from django.db import models

from .firm import CpaFirm


class ClientAccount(models.Model):
    """A managed business belonging to a CPA firm."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        CpaFirm,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    client_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["client_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["firm", "client_name"], name="uniq_client_name_per_firm"
            )
        ]
        verbose_name = "client account"
        verbose_name_plural = "client accounts"

    def __str__(self) -> str:
        return self.client_name