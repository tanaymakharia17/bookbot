"""API URL routes (v1)."""
from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("clients/", views.ClientListView.as_view(), name="client-list"),
    path("clients/<uuid:pk>/", views.ClientDetailView.as_view(), name="client-detail"),
    path("submissions/", views.SubmissionListView.as_view(), name="submission-list"),
    path("submissions/<uuid:pk>/", views.SubmissionDetailView.as_view(), name="submission-detail"),
    path("submissions/<uuid:pk>/chat/", views.SubmissionChatView.as_view(), name="submission-chat"),
    path("submissions/<uuid:pk>/documents/", views.SubmissionDocumentsView.as_view(), name="submission-documents"),
    path("submissions/<uuid:pk>/plan/files/", views.SubmissionPlanFilesView.as_view(), name="submission-plan-files"),
    path("submissions/<uuid:pk>/plan/tasks/", views.SubmissionPlanTasksView.as_view(), name="submission-plan-tasks"),
    path("submissions/<uuid:pk>/plan/ops/<str:op_id>/", views.SubmissionPlanOpView.as_view(), name="submission-plan-op"),
    path("submissions/<uuid:pk>/plan/execute/", views.SubmissionPlanExecuteView.as_view(), name="submission-plan-execute"),
    path("submissions/<uuid:pk>/plan/discard/", views.SubmissionPlanDiscardView.as_view(), name="submission-plan-discard"),
    path("submissions/<uuid:pk>/journal_preview/", views.SubmissionJournalPreviewView.as_view(), name="submission-journal-preview"),
    path("submissions/<uuid:pk>/approve/", views.SubmissionApproveView.as_view(), name="submission-approve"),
    path("submissions/<uuid:pk>/resolve_compliance/", views.SubmissionResolveComplianceView.as_view(), name="submission-resolve-compliance"),
    path("ledger/", views.LedgerListView.as_view(), name="ledger-list"),
    path("ledger/<str:entry_id>/", views.LedgerDetailView.as_view(), name="ledger-detail"),
    path("uploads/available/", views.AvailableFilesView.as_view(), name="uploads-available"),
    path("uploads/", views.UploadPageView.as_view(), name="uploads"),
]