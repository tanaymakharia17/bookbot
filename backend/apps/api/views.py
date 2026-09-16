"""API views."""
import uuid as uuid_lib

from django.http import HttpResponse
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.fsm import SubmissionFSM
from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.core.state import SubmissionState
from apps.core.tasks import extract_submission
from apps.services.agent import respond
from apps.services.extraction import ensure_tasks, extract
from apps.services.journal import preview as journal_preview
from apps.services.ledger import get_entry as get_ledger_entry
from apps.services.ledger import list_entries as list_ledger_entries
from apps.services.review import approve as approve_submission
from apps.services.review import resolve_compliance as resolve_submission_compliance
from apps.services.storage import available_files, import_named_files, save_upload_stream
from apps.services.plan import (
    discard_plan,
    execute_plan,
    remove_plan_op,
    stage_files,
    stage_task_add,
    stage_task_remove,
    stage_task_toggle,
)

from .serializers import (
    ClientSerializer,
    SubmissionCreateSerializer,
    SubmissionDetailSerializer,
    SubmissionListSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Liveness probe."""
    return Response({"status": "ok", "service": "bookbot-backend"})


class ClientListView(generics.ListCreateAPIView):
    """List and create managed companies for the default firm."""

    serializer_class = ClientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return ClientAccount.objects.filter(firm=get_default_firm())

    def perform_create(self, serializer):
        serializer.save(firm=get_default_firm())


class ClientDetailView(generics.RetrieveAPIView):
    """Retrieve a single managed company."""

    serializer_class = ClientSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return ClientAccount.objects.filter(firm=get_default_firm())


class SubmissionListView(generics.ListCreateAPIView):
    """List and create submissions, optionally filtered by client and state."""

    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubmissionCreateSerializer
        return SubmissionListSerializer

    def perform_create(self, serializer):
        submission = serializer.save()
        import_named_files(submission.id, submission.file_names or [])
        try:
            extract_submission.delay(str(submission.id))
        except Exception:  # noqa: BLE001 - broker unavailable: extract inline
            extract(submission)

    def get_queryset(self):
        queryset = Submission.objects.select_related("client").all()

        client_id = self.request.query_params.get("client")
        if client_id:
            try:
                uuid_lib.UUID(str(client_id))
            except (ValueError, TypeError):
                return Submission.objects.none()
            queryset = queryset.filter(client_id=client_id)

        state = self.request.query_params.get("state")
        if state:
            queryset = queryset.filter(state=state)

        return queryset


class SubmissionDetailView(generics.RetrieveAPIView):
    """Retrieve a single submission with its full workpaper data."""

    serializer_class = SubmissionDetailSerializer
    permission_classes = [AllowAny]
    queryset = Submission.objects.select_related("client").all()

    def retrieve(self, request, *args, **kwargs):
        submission = self.get_object()
        ensure_tasks(submission)
        return Response(self.get_serializer(submission).data)


class SubmissionChatView(APIView):
    """Chat history (GET) and send a message to the review agent (POST)."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response([])
        return Response(submission.chat_messages or [])

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "Message cannot be empty."})
        if submission.state == SubmissionState.RAW:
            return Response({"error": "Extraction is still in progress. Try again shortly."})
        if submission.state == SubmissionState.COMMITTED:
            return Response(
                {"error": "This submission has been posted. Start a new submission for further work."}
            )

        messages = list(submission.chat_messages or [])
        messages.append({"role": "cpa", "content": message})
        reply = respond(submission, message)
        messages.append({"role": "agent", "content": reply})
        submission.chat_messages = messages

        if submission.state == SubmissionState.EXTRACTED:
            SubmissionFSM.transition(submission, SubmissionState.NEEDS_REVIEW)

        submission.save()
        return Response({
            "reply": reply,
            "submission": SubmissionDetailSerializer(submission).data,
        })


class SubmissionPlanFilesView(APIView):
    """Stage documents to save or keep as reference on the pending plan."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        result = stage_files(submission, request.data.get("files") or [])
        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({
            "submission": SubmissionDetailSerializer(submission).data,
            "proposed": result["proposed"],
        })


class SubmissionPlanTasksView(APIView):
    """Stage a checklist change: add, toggle, or remove."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        data = request.data
        if data.get("remove"):
            result = stage_task_remove(submission, data.get("task_id"))
        elif data.get("task_id") is not None:
            result = stage_task_toggle(submission, data.get("task_id"), bool(data.get("done")))
        else:
            result = stage_task_add(submission, data.get("title"))

        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({"submission": SubmissionDetailSerializer(submission).data})


class SubmissionPlanOpView(APIView):
    """Remove a single staged operation from the pending plan."""

    permission_classes = [AllowAny]

    def delete(self, request, pk, op_id):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        result = remove_plan_op(submission, op_id)
        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({"submission": SubmissionDetailSerializer(submission).data})


class SubmissionPlanExecuteView(APIView):
    """Apply the pending plan to the committed submission state."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        result = execute_plan(submission)
        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({"submission": SubmissionDetailSerializer(submission).data})


class SubmissionPlanDiscardView(APIView):
    """Discard the pending plan without changing anything."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        discard_plan(submission)
        submission.save()
        return Response({"submission": SubmissionDetailSerializer(submission).data})


class SubmissionJournalPreviewView(APIView):
    """Preview the journal entry for the projected line items."""

    permission_classes = [AllowAny]

    def get(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})
        return Response(journal_preview(submission) or {})


class SubmissionApproveView(APIView):
    """Approve the submission and post its journal entry to the ledger."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        result = approve_submission(submission)
        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({
            "submission": SubmissionDetailSerializer(submission).data,
            "journal_entry": result["journal_entry"],
        })


class SubmissionResolveComplianceView(APIView):
    """Mark a compliance blocker resolved and return the submission to review."""

    permission_classes = [AllowAny]

    def post(self, request, pk):
        submission = Submission.objects.filter(pk=pk).first()
        if not submission:
            return Response({"error": "Submission not found."})

        result = resolve_submission_compliance(submission)
        if result.get("error"):
            return Response(result)

        submission.save()
        return Response({"submission": SubmissionDetailSerializer(submission).data})


class LedgerListView(APIView):
    """List posted journal entries, optionally filtered by client."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(list_ledger_entries(request.query_params.get("client")))


class LedgerDetailView(APIView):
    """Retrieve a single ledger entry with its journal lines."""

    permission_classes = [AllowAny]

    def get(self, request, entry_id):
        entry = get_ledger_entry(entry_id)
        if not entry:
            return Response({"error": "Ledger entry not found."}, status=404)
        return Response(entry)


class AvailableFilesView(APIView):
    """List documents available on the server for attachment without browser upload."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"files": available_files()})


_UPLOAD_FORM = """<!doctype html>
<html><head><meta charset="utf-8"><title>Bookbot upload</title>
<style>body{{font-family:system-ui,sans-serif;background:#F5F7FA;color:#101828;padding:40px}}
.card{{max-width:560px;margin:0 auto;background:#fff;border:1px solid #E4E7EC;border-radius:12px;padding:24px}}
h1{{font-size:1.2rem;margin:0 0 6px}}p{{color:#667085;font-size:.9rem}}
input[type=file]{{margin:14px 0;display:block}}
button{{background:#1570EF;color:#fff;border:0;border-radius:8px;padding:10px 16px;font-weight:600;cursor:pointer}}
a{{color:#1570EF}}</style></head>
<body><div class="card">
<h1>Upload documents</h1>
<p>Files land in the Bookbot staging area. After uploading, pick them in the app under
<b>“Can't upload? Attach files already on the server”</b>.</p>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" multiple required>
  <button type="submit">Upload</button>
</form>
<p style="margin-top:16px"><a href="/api/v1/uploads/">Upload more</a></p>
</div></body></html>"""


class UploadPageView(APIView):
    """Browser upload page served by Django (bypasses Streamlit's upload endpoint)."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return HttpResponse(_UPLOAD_FORM, content_type="text/html")

    def post(self, request):
        saved = [save_upload_stream(f).name for f in request.FILES.getlist("file")]
        if request.query_params.get("json"):
            return Response({"saved": saved})
        if not saved:
            body = "<p>No file received.</p>"
        else:
            body = "<p>Uploaded: <b>" + ", ".join(saved) + "</b></p>"
        return HttpResponse(
            f"<html><body style='font-family:system-ui;padding:40px'>{body}"
            "<p><a href='/api/v1/uploads/'>Upload more</a> · "
            "<a href='/api/v1/uploads/available/'>List staged files</a></p></body></html>",
            content_type="text/html",
        )