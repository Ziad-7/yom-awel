"""Telegram update translation; no grading or progression rules."""

import hashlib
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx

from yom_awel.application.commands import ProcessSubmissionCommand
from yom_awel.application.models import CurrentTaskResult, ProcessingState
from yom_awel.domain.contracts import SubmissionOutcome
from yom_awel.domain.entities import Artifact
from yom_awel.domain.enums import Channel, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import dataset
from yom_awel.transport.artifact_validation import validate_content
from yom_awel.transport.auth import Identity
from yom_awel.transport.dependencies import Services
from yom_awel.transport.models import OnboardInput

MAX_BYTES = 5 * 1024 * 1024


class BotClient(Protocol):
    async def send(self, chat_id: int, text: str) -> None: ...
    async def send_file(self, chat_id: int, filename: str, content: bytes) -> None: ...
    async def download(self, file_id: str) -> bytes: ...


class TelegramClient:
    def __init__(self, token: str) -> None:
        if not token:
            raise DomainError("unavailable", "Telegram is not configured")
        self._token = token

    async def send(self, chat_id: int, text: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4000]},
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise DomainError("unavailable", "Telegram delivery unavailable")

    async def download(self, file_id: str) -> bytes:
        if not isinstance(file_id, str) or not file_id.strip():
            raise DomainError("unsupported_artifact", "Invalid file id")
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._token}/getFile", json={"file_id": file_id}
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise DomainError("unavailable", "Telegram file unavailable")
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
                raise DomainError("unavailable", "Telegram file unavailable")
            metadata = data["result"]
            path = metadata.get("file_path", "")
            file_size = metadata.get("file_size", 0)
            if (
                not isinstance(path, str)
                or not path
                or ".." in path
                or ":" in path
                or path.startswith("/")
                or not isinstance(file_size, int)
                or file_size > MAX_BYTES
                or file_size < 0
            ):
                raise DomainError("unsupported_artifact", "Invalid file")
            content = bytearray()
            async with client.stream(
                "GET", f"https://api.telegram.org/file/bot{self._token}/{path}"
            ) as download:
                if download.status_code != 200:
                    raise DomainError("unavailable", "Download unavailable")
                async for chunk in download.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_BYTES:
                        raise DomainError("too_large", "File exceeds upload limit")
            return bytes(content)

    async def send_file(self, chat_id: int, filename: str, content: bytes) -> None:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "sql": "text/plain",
            "txt": "text/plain",
        }.get(ext, "application/octet-stream")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._token}/sendDocument",
                data={"chat_id": str(chat_id)},
                files={"document": (filename, content, mime)},
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise DomainError("unavailable", "Telegram delivery unavailable")


class TelegramAdapter:
    def __init__(self, services: Services, client: BotClient) -> None:
        self.services, self.client = services, client

    async def handle(self, update: dict[str, Any]) -> None:
        if not isinstance(update.get("update_id"), int):
            raise DomainError("invalid_request", "Invalid update")
        message = update.get("message")
        if not isinstance(message, dict):
            return
        sender, chat = message.get("from", {}), message.get("chat", {})
        if (
            not isinstance(sender.get("id"), int)
            or chat.get("type") != "private"
            or sender.get("id") != chat.get("id")
        ):
            return
        chat_id = chat["id"]
        identity = Identity("telegram", str(sender["id"]))
        learner = await self.services.onboard(
            identity, OnboardInput(display_name=str(sender.get("first_name") or "متدرّب")[:80])
        )
        text = str(message.get("text", "")).strip()
        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0]
        current = await self._current_task(learner.learner_id)
        if command == "/tasks":
            await self.client.send(
                chat_id,
                "المهام المتاحة:\n"
                + "\n".join(
                    f"/task {item.task_id} — {item.title_ar}"
                    for item in self.services.catalog.tasks()
                ),
            )
            return
        if command == "/task" and argument.strip():
            try:
                current = await self.services.start.execute(learner.learner_id, argument.strip())
            except DomainError:
                await self.client.send(chat_id, "المهمة غير متاحة. استخدم /tasks لعرض المهام.")
                return
        if command in ("/start", "/task"):
            task = self.services.catalog.get(current.task.task_id) if current.task else None
            formats = (
                " أو ".join(ext.upper() for ext in task.package.limits.extensions) if task else ""
            )
            await self.client.send(
                chat_id,
                "أهلاً بيك في يوم أول!\n"
                + (task.title_ar if task else "المهمة مش متاحة دلوقتي.")
                + f"\nنزّل الملف، نفّذ المهمة، وابعته هنا {formats}. "
                "استخدم /tasks لتغيير المهمة و /skills لمهاراتك.",
            )
            if task:
                file = dataset(task, "csv")
                await self.client.send_file(chat_id, file.filename, file.content)
            return
        if command in ("/skills", "/status"):
            profile = await self.services.skills.execute(learner.learner_id)
            await self.client.send(
                chat_id,
                "مهاراتك\n"
                + (
                    "\n".join(f"{item.skill_id}: {item.score}/100" for item in profile.skills)
                    or "لسه مفيش مهام مكتملة."
                ),
            )
            return
        document = message.get("document")
        if not isinstance(document, dict) or current.task is None:
            await self.client.send(chat_id, "استخدم /task لعرض المهمة ثم ابعت ملف الحل.")
            return

        file_id = document.get("file_id")
        file_unique_id = document.get("file_unique_id")
        file_name = document.get("file_name")
        file_size = document.get("file_size")
        if (
            not isinstance(file_id, str)
            or not file_id.strip()
            or not isinstance(file_unique_id, str)
            or not file_unique_id.strip()
            or not isinstance(file_name, str)
            or not file_name.strip()
        ):
            await self.client.send(chat_id, "بيانات الملف من تليجرام غير صالحة.")
            return

        filename = file_name.strip()
        if (
            any(char in filename for char in ("/", "\\", "\x00"))
            or ".." in filename
            or "." not in filename
        ):
            await self.client.send(chat_id, "صيغة الملف لا تطابق المهمة الحالية.")
            return

        allowed = self.services.catalog.get(current.task.task_id).package.limits.extensions
        if filename.rsplit(".", 1)[-1].lower() not in allowed:
            await self.client.send(chat_id, "صيغة الملف لا تطابق المهمة الحالية.")
            return

        if not isinstance(file_size, int) or not 0 < file_size <= MAX_BYTES:
            await self.client.send(chat_id, "حجم الملف لازم يكون أقل من أو يساوي 5 ميجابايت.")
            return

        key = f"telegram:{update['update_id']}:{file_unique_id}"
        async with self.services.factory() as uow:
            prior = await uow.submissions.get_reservation(learner.learner_id, key)
        if prior and prior.outcome:
            await self._result(chat_id, prior.outcome)
            return

        content = await self.client.download(file_id)
        if not 0 < len(content) <= MAX_BYTES or len(content) != file_size:
            raise DomainError("artifact_integrity_failure", "File size mismatch")

        fallback_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "sql": "text/plain",
            "txt": "text/plain",
        }
        extension = filename.rsplit(".", 1)[-1].lower()
        content_type = str(document.get("mime_type") or fallback_types[extension])
        try:
            validate_content(filename, content_type, content)
        except DomainError:
            await self.client.send(chat_id, "محتوى الملف أو نوعه غير صالح. ارفع ملف حل سليم.")
            return

        artifact = Artifact(
            artifact_id=uuid5(NAMESPACE_URL, f"{learner.learner_id}:{key}"),
            learner_id=learner.learner_id,
            filename=filename,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        async with self.services.factory() as uow:
            existing = await uow.artifacts.get(artifact.artifact_id, learner.learner_id)
            if existing is None:
                await uow.artifacts.put(artifact, content)
            elif existing != artifact:
                raise DomainError("idempotency_conflict", "Update changed")
            await uow.commit()

        try:
            result = await self.services.submissions.execute(
                ProcessSubmissionCommand(
                    learner_id=learner.learner_id,
                    task_version_id=current.task.task_version_id,
                    artifact_id=artifact.artifact_id,
                    artifact_sha256=artifact.sha256,
                    channel=Channel.TELEGRAM,
                    idempotency_key=key,
                    channel_event_id=str(update["update_id"]),
                    learner_note=str(message.get("caption", ""))[:500],
                ),
                str(uuid4()),
            )
        except DomainError as error:
            if error.code == "invalid_status":
                await self.client.send(
                    chat_id, "المهمة مكتملة بالفعل. استخدم /tasks لاختيار مهمة تانية."
                )
                return
            raise

        if isinstance(result, ProcessingState):
            await self.client.send(chat_id, "التسليم قيد المراجعة، جرّب تاني بعد شوية.")
        else:
            await self._result(chat_id, result)

    async def _current_task(self, learner_id: UUID) -> CurrentTaskResult:
        """Telegram has no task picker, so a READY learner starts the first published task."""

        current = await self.services.tasks.execute(learner_id)
        tasks = self.services.catalog.tasks()
        if current.task is None and current.status == LearnerStatus.READY and tasks:
            return await self.services.start.execute(learner_id, tasks[0].task_id)
        return current

    async def _result(self, chat_id: int, result: SubmissionOutcome) -> None:
        decision = "التسليم مقبول" if result.evaluation.passed else "محتاج تعديل وإعادة تسليم"
        label = "إرشادات بديلة" if result.feedback.used_fallback else "ملاحظات المدرب"
        await self.client.send(
            chat_id,
            f"{decision} — {result.evaluation.score}/100\n{label}\n{result.feedback.feedback_text}\n/skills لعرض مهاراتك",
        )
