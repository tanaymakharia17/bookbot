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
    path("submissions/<uuid:pk>/plan/files/", views.SubmissionPlanFilesView.as_view(), name="submission-plan-files"),
    path("submissions/<uuid:pk>/plan/tasks/", views.SubmissionPlanTasksView.as_view(), name="submission-plan-tasks"),
    path("submissions/<uuid:pk>/plan/ops/<str:op_id>/", views.SubmissionPlanOpView.as_view(), name="submission-plan-op"),
    path("submissions/<uuid:pk>/plan/execute/", views.SubmissionPlanExecuteView.as_view(), name="submission-plan-execute"),
    path("submissions/<uuid:pk>/plan/discard/", views.SubmissionPlanDiscardView.as_view(), name="submission-plan-discard"),
]