"""Backend access layer.

``get_api()`` returns a client whose methods match the future Django REST
API. Flipping ``config.USE_MOCK`` to ``false`` swaps in a real HTTP client
without touching any view code.
"""

from __future__ import annotations

from typing import Any

from config import API_MODE, BACKEND_URL
from mock_backend import MockBackend


class BaseBackend:
    def list_clients(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def create_client(self, name: str) -> dict[str, Any]:
        raise NotImplementedError

    def list_submissions(self, client_id: str, state_filter: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_submission(self, submission_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def create_submission(self, client_id: str, file_names: list[str], raw_input: str) -> dict[str, Any]:
        raise NotImplementedError

    def chat_history(self, submission_id: str) -> list[dict[str, str]]:
        raise NotImplementedError

    def chat(self, submission_id: str, message: str) -> dict[str, Any]:
        raise NotImplementedError

    def stage_files(self, submission_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError

    def stage_task_add(self, submission_id: str, title: str) -> dict[str, Any]:
        raise NotImplementedError

    def stage_task_toggle(self, submission_id: str, task_id: str, done: bool) -> dict[str, Any]:
        raise NotImplementedError

    def stage_task_remove(self, submission_id: str, task_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def remove_plan_op(self, submission_id: str, op_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def execute_plan(self, submission_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def discard_plan(self, submission_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def preview_journal(self, submission_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def approve(self, submission_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def resolve_compliance(self, submission_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def list_ledger_entries(self, client_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_ledger_entry(self, entry_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class RealBackend(BaseBackend):
    """HTTP client for the Django backend. Enabled once the API exists."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, **params):
        import requests

        resp = requests.get(f"{self.base_url}{path}", params=params, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json=None, files=None, data=None):
        import requests

        resp = requests.post(
            f"{self.base_url}{path}", json=json, files=files, data=data, timeout=120
        )
        if resp.status_code >= 400:
            return {"error": _format_error(resp)}
        return resp.json()

    def _delete(self, path: str):
        import requests

        resp = requests.delete(f"{self.base_url}{path}", timeout=30)
        if resp.status_code >= 400:
            return {"error": _format_error(resp)}
        return resp.json()

    def list_clients(self) -> list[dict[str, Any]]:
        return self._get("/api/v1/clients/")

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        return self._get(f"/api/v1/clients/{client_id}/")

    def create_client(self, name: str) -> dict[str, Any]:
        import requests

        resp = requests.post(f"{self.base_url}/api/v1/clients/", json={"name": name}, timeout=30)
        if resp.status_code >= 400:
            return {"error": _format_error(resp)}
        return resp.json()

    def list_submissions(self, client_id: str, state_filter: str | None = None) -> list[dict[str, Any]]:
        params = {"client": client_id}
        if state_filter and state_filter != "all":
            params["state"] = state_filter
        return self._get("/api/v1/submissions/", **params)

    def get_submission(self, submission_id: str) -> dict[str, Any] | None:
        return self._get(f"/api/v1/submissions/{submission_id}/")

    def create_submission(self, client_id: str, file_names: list[str], raw_input: str) -> dict[str, Any]:
        return self._post("/api/v1/submissions/", json={
            "client_id": client_id, "file_names": file_names, "raw_input": raw_input,
        })

    def chat_history(self, submission_id: str) -> list[dict[str, str]]:
        return self._get(f"/api/v1/submissions/{submission_id}/chat/")

    def chat(self, submission_id: str, message: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/chat/", json={"message": message})

    def stage_files(self, submission_id: str, files: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/files/", json={"files": files})

    def stage_task_add(self, submission_id: str, title: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/tasks/", json={"title": title})

    def stage_task_toggle(self, submission_id: str, task_id: str, done: bool) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/tasks/", json={"task_id": task_id, "done": done})

    def stage_task_remove(self, submission_id: str, task_id: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/tasks/", json={"task_id": task_id, "remove": True})

    def remove_plan_op(self, submission_id: str, op_id: str) -> dict[str, Any]:
        return self._delete(f"/api/v1/submissions/{submission_id}/plan/ops/{op_id}/")

    def execute_plan(self, submission_id: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/execute/")

    def discard_plan(self, submission_id: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/plan/discard/")

    def preview_journal(self, submission_id: str) -> dict[str, Any] | None:
        return self._get(f"/api/v1/submissions/{submission_id}/journal_preview/")

    def approve(self, submission_id: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/approve/")

    def resolve_compliance(self, submission_id: str) -> dict[str, Any]:
        return self._post(f"/api/v1/submissions/{submission_id}/resolve_compliance/")

    def list_ledger_entries(self, client_id: str | None = None) -> list[dict[str, Any]]:
        params = {"client": client_id} if client_id else {}
        return self._get("/api/v1/ledger/", **params)

    def get_ledger_entry(self, entry_id: str) -> dict[str, Any] | None:
        return self._get(f"/api/v1/ledger/{entry_id}/")


_api: BaseBackend | None = None


class HybridBackend(MockBackend):
    """Clients hit the Django API; everything else stays on the mock."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self._real = RealBackend(base_url)

    def list_clients(self) -> list[dict[str, Any]]:
        return self._real.list_clients()

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        return self._real.get_client(client_id)

    def create_client(self, name: str) -> dict[str, Any]:
        return self._real.create_client(name)

    def create_submission(self, client_id: str, file_names: list[str], raw_input: str) -> dict[str, Any]:
        # Register the real client locally so mock review/ledger logic can resolve it.
        client = self._real.get_client(client_id)
        if client:
            self.clients[client_id] = {
                "id": client_id,
                "name": client.get("name", ""),
                "submission_count": 0,
                "last_activity": "",
                "counts": {},
            }
        return super().create_submission(client_id, file_names, raw_input)


def _format_error(resp) -> str:
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        return resp.text or f"HTTP {resp.status_code}"
    if isinstance(data, dict):
        messages = []
        for value in data.values():
            if isinstance(value, list):
                messages.extend(str(v) for v in value)
            else:
                messages.append(str(value))
        if messages:
            return " ".join(messages)
    return str(data)


def get_api() -> BaseBackend:
    global _api
    if _api is None:
        if API_MODE == "real":
            _api = RealBackend(BACKEND_URL)
        elif API_MODE == "hybrid":
            _api = HybridBackend(BACKEND_URL)
        else:
            _api = MockBackend()
    return _api