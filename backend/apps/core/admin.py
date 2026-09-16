from django.contrib import admin

from .models import ClientAccount, CpaFirm


@admin.register(CpaFirm)
class CpaFirmAdmin(admin.ModelAdmin):
    list_display = ("firm_name", "created_at", "id")
    search_fields = ("firm_name",)


@admin.register(ClientAccount)
class ClientAccountAdmin(admin.ModelAdmin):
    list_display = ("client_name", "firm", "capex_threshold", "created_at")
    list_filter = ("firm",)
    search_fields = ("client_name",)