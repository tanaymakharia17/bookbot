from django.contrib import admin

from .models import ClientAccount, CpaFirm, Submission


@admin.register(CpaFirm)
class CpaFirmAdmin(admin.ModelAdmin):
    list_display = ("firm_name", "created_at", "id")
    search_fields = ("firm_name",)


@admin.register(ClientAccount)
class ClientAccountAdmin(admin.ModelAdmin):
    list_display = ("client_name", "firm", "created_at")
    list_filter = ("firm",)
    search_fields = ("client_name",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "state", "vendor", "created_at")
    list_filter = ("state", "client__firm")
    search_fields = ("vendor", "raw_input")
    readonly_fields = ("created_at", "updated_at")