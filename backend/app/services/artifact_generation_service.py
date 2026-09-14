from __future__ import annotations

import csv
import io
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_execution import ActionExecution
from app.services.file_storage_service import FileStorageService
from app.services.workspace_activity_service import WorkspaceActivityService
from app.tools.pdf_generator import PDFGenerator

SUPPORTED_ARTIFACT_TYPES = {"pdf", "txt", "markdown", "csv"}
FILE_EXTENSION_MAP = {"pdf": ".pdf", "txt": ".txt", "markdown": ".md", "csv": ".csv"}
MIME_TYPES = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "markdown": "text/markdown",
    "csv": "text/csv",
}


class ArtifactGenerationService:
    """Real artifact generator that writes files to the existing storage layer and records metadata."""

    def __init__(self, session: AsyncSession | None = None, base_path: str = "/tmp/synzept-artifacts") -> None:
        self.session = session
        self.storage = FileStorageService(base_path=base_path)

    async def generate(
        self,
        *,
        user_id: UUID | str,
        execution_id: UUID | str | None,
        request_context: str | None,
        artifact_type: str,
        filename: str | None,
        content: Any,
        action: ActionExecution | None = None,
    ) -> dict[str, Any]:
        artifact_type = (artifact_type or "").strip().lower()
        user_uuid = self._coerce_uuid(user_id)
        if user_uuid is None:
            return {"success": False, "error": "user_id is required for artifact generation"}

        if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
            error = f"Unsupported artifact type: {artifact_type}. Supported types: {', '.join(sorted(SUPPORTED_ARTIFACT_TYPES))}"
            if action is not None:
                await self._mark_failed(action, error)
            return {"success": False, "error": error, "artifact_type": artifact_type}

        if action is None and self.session is not None and execution_id is not None:
            action = await self.session.get(ActionExecution, execution_id)

        filename = self._sanitize_filename(filename, artifact_type)
        payload = self._normalize_content(artifact_type, content)
        if not payload:
            error = "Artifact content is empty. Nothing was generated."
            if action is not None:
                await self._mark_failed(action, error)
            return {"success": False, "error": error, "artifact_type": artifact_type, "filename": filename}

        try:
            file_path = self._resolve_storage_path(user_uuid, filename)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            serialized = self._serialize(artifact_type, payload)
            if len(serialized) > 20 * 1024 * 1024:
                error = "Artifact is too large to store. Max size is 20 MB."
                if action is not None:
                    await self._mark_failed(action, error)
                return {"success": False, "error": error, "artifact_type": artifact_type, "filename": filename}
            with open(file_path, "wb") as handle:
                handle.write(serialized)
            if not os.path.exists(file_path) or os.path.getsize(file_path) <= 0:
                error = "Artifact generation created an empty file."
                if action is not None:
                    await self._mark_failed(action, error)
                return {"success": False, "error": error, "artifact_type": artifact_type, "filename": filename}

            file_record = self.storage.save_file(
                user_uuid,
                file_path,
                {
                    "id": str(uuid.uuid4()),
                    "title": self._display_title(filename),
                    "description": request_context or "Generated artifact",
                    "file_type": MIME_TYPES[artifact_type],
                    "action_id": str(action.id) if action is not None else None,
                    "execution_id": str(execution_id) if execution_id is not None else None,
                    "task_id": (action.metadata_ or {}).get("task_id") if action is not None else None,
                },
            )
            if not file_record:
                error = "Artifact storage failed while saving the generated file."
                if action is not None:
                    await self._mark_failed(action, error)
                return {"success": False, "error": error, "artifact_type": artifact_type, "filename": filename}

            artifact_id = file_record["id"] or str(uuid.uuid4())
            metadata = {
                "artifact_id": artifact_id,
                "execution_id": str(execution_id) if execution_id is not None else None,
                "filename": filename,
                "file_type": MIME_TYPES[artifact_type],
                "mime_type": MIME_TYPES[artifact_type],
                "file_size": os.path.getsize(file_path),
                "storage_path": file_path,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": request_context or "artifact_generation_service",
            }
            if action is not None:
                existing = list((action.metadata_ or {}).get("artifacts") or [])
                action.metadata_ = {**(action.metadata_ or {}), "artifacts": [*existing, metadata]}
                action.output = f"Created: {filename}"
                action.progress = max(action.progress or 0, 100)
                action.status = "completed"
                action.completed_at = action.completed_at or datetime.now(timezone.utc)
                if self.session is not None:
                    await WorkspaceActivityService(self.session).record(
                        user_id=user_uuid,
                        action="artifact_created",
                        title=filename,
                        detail=f"Generated a real {artifact_type.upper()} artifact for this execution.",
                        project_id=action.project_id,
                        task_id=(action.metadata_ or {}).get("task_id"),
                        execution_id=action.id,
                        metadata={"artifact_id": artifact_id, "filename": filename, "mime_type": MIME_TYPES[artifact_type], "execution_id": str(action.id)},
                    )
                    await self.session.flush()
            return {
                "success": True,
                "artifact_id": artifact_id,
                "execution_id": str(execution_id) if execution_id is not None else None,
                "filename": filename,
                "file_type": MIME_TYPES[artifact_type],
                "mime_type": MIME_TYPES[artifact_type],
                "file_size": os.path.getsize(file_path),
                "storage_path": file_path,
                "created_at": metadata["created_at"],
                "source": request_context or "artifact_generation_service",
                "file_path": file_path,
                "metadata": metadata,
            }
        except Exception as exc:  # pragma: no cover - safety guard
            error = f"Artifact generation failed: {exc}"
            if action is not None:
                await self._mark_failed(action, error)
            return {"success": False, "error": error, "artifact_type": artifact_type, "filename": filename}

    @staticmethod
    def _coerce_uuid(value: UUID | str | None) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sanitize_filename(filename: str | None, artifact_type: str) -> str:
        desired_extension = FILE_EXTENSION_MAP.get(artifact_type, f".{artifact_type}")
        candidate = (filename or f"artifact{desired_extension}").strip()
        if not candidate:
            candidate = f"artifact{desired_extension}"
        candidate = candidate.replace("/", "_").replace("\\", "_")
        candidate = re.sub(r"[^A-Za-z0-9_.-]+", "-", candidate)
        lower_candidate = candidate.lower()
        if lower_candidate.endswith(".markdown") and artifact_type == "markdown":
            candidate = candidate[:-len(".markdown")] + desired_extension
        if not lower_candidate.endswith(tuple(FILE_EXTENSION_MAP.values())):
            if artifact_type in FILE_EXTENSION_MAP:
                candidate = f"{candidate}{desired_extension}" if not lower_candidate.endswith(desired_extension) else candidate
        if candidate in {".", ".."} or candidate.strip() == "":
            candidate = f"artifact{desired_extension}"
        return candidate

    @staticmethod
    def _display_title(filename: str) -> str:
        return os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()

    @staticmethod
    def _normalize_content(artifact_type: str, content: Any) -> Any:
        if artifact_type == "pdf":
            if content is None:
                return []
            if isinstance(content, list):
                return content
            if isinstance(content, str):
                if not content.strip():
                    return []
                return [{"number": "1", "title": "Generated PDF", "explanation": content, "skills": []}]
            return [{"number": "1", "title": "Generated PDF", "explanation": str(content), "skills": []}]
        if artifact_type in {"txt", "markdown"}:
            if content is None:
                return ""
            return str(content)
        if artifact_type == "csv":
            if content is None:
                return []
            return content
        return content

    @staticmethod
    def _serialize(artifact_type: str, payload: Any) -> bytes:
        if artifact_type == "pdf":
            items = payload if isinstance(payload, list) else [{"number": "1", "title": "Generated PDF", "explanation": str(payload), "skills": []}]
            output_path = f"/tmp/synzept-artifact-{uuid.uuid4().hex}.pdf"
            generator = PDFGenerator()
            generated = generator.generate(output_path=output_path, title="Generated Artifact", content=items)
            if not generated or not os.path.exists(output_path):
                raise ValueError("PDF generation failed")
            with open(output_path, "rb") as handle:
                content = handle.read()
            try:
                os.remove(output_path)
            except OSError:
                pass
            return content

        if artifact_type in {"txt", "markdown"}:
            return str(payload).encode("utf-8")

        if artifact_type == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            if isinstance(payload, list):
                if not payload:
                    raise ValueError("CSV content is empty")
                if isinstance(payload[0], dict):
                    headers = list(payload[0].keys())
                    writer.writerow(headers)
                    for row in payload:
                        writer.writerow([row.get(header, "") for header in headers])
                else:
                    for row in payload:
                        writer.writerow(row)
            else:
                raise ValueError("CSV payload must be a list of rows or dictionaries")
            return buffer.getvalue().encode("utf-8")

        raise ValueError(f"Unsupported artifact type: {artifact_type}")

    def _resolve_storage_path(self, user_id: UUID, filename: str) -> str:
        root = Path(self.storage.base_path) / str(user_id)
        root.mkdir(parents=True, exist_ok=True)
        return str(root / filename)

    async def _mark_failed(self, action: ActionExecution, error: str) -> None:
        action.status = "failed"
        action.error = error
        action.progress = max(action.progress or 0, 35)
        action.failed_at = action.failed_at or datetime.now(timezone.utc)
        if self.session is not None:
            await self.session.flush()
