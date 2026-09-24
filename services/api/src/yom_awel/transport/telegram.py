"""Telegram update translation; no grading or progression rules."""

import hashlib
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx

from yom_awel.application.commands import ProcessSubmissionCommand
from yom_awel.application.models import ProcessingState
from yom_awel.domain.contracts import SubmissionOutcome
from yom_awel.domain.entities import Artifact
from yom_awel.domain.enums import Channel
from yom_awel.domain.errors import DomainError
from yom_awel.transport.artifact_validation import validate_content
from yom_awel.transport.auth import Identity
from yom_awel.transport.dependencies import Services
from yom_awel.transport.fakes import DIRTY_CSV
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
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._token}/getFile", json={"file_id": file_id}
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise DomainError("unavailable", "Telegram file unavailable")
            metadata = response.json()["result"]
            path = metadata.get("file_path", "")
            if (
                not path
                or ".." in path
                or ":" in path
                or path.startswith("/")
                or metadata.get("file_size", 0) > MAX_BYTES
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
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self._token}/sendDocument",
                data={"chat_id": str(chat_id)},
                files={"document": (filename, content, "text/csv")},
            )
            if response.status_code != 200 or not response.json().get("ok"):
                raise DomainError("unavailable", "Telegram delivery unavailable")


class TelegramAdapter:
    def __init__(self, services: Services, client: BotClient) -> None:
        self.services, self.client = services, client

    async def handle(self, update: dict[str, Any]) -> None:
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
        if not isinstance(update.get("update_id"), int):
            raise DomainError("invalid_request", "Invalid update")
        identity = Identity("telegram", str(sender["id"]))
        learner = await self.services.onboard(
            identity, OnboardInput(display_name=str(sender.get("first_name") or "متدرّب")[:80])
        )
        text = str(message.get("text", "")).split("@", 1)[0]
        current = await self.services.tasks.execute(learner.learner_id)
        if text in ("/start", "/task"):
            instructions = (
                current.task.instructions_ar if current.task else "المهمة مش متاحة دلوقتي."
            )
            await self.client.send(
                chat_id,
                "أهلاً بيك في يوم أول!\n"
                + instructions
                + "\nابعت ملف CSV أو XLSX، أو استخدم /skills.",
            )
            if self.services.simulated:
                await self.client.send(
                    chat_id, "ملف محاكاة لاختبار رحلة التسليم، مش تقييم مهارة فعلي."
                )
                await self.client.send_file(chat_id, "sales-demo.csv", DIRTY_CSV)
            return
        if text in ("/skills", "/status"):
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
            await self.client.send(chat_id, "استخدم /task لعرض المهمة أو ابعت ملف CSV أو XLSX.")
            return
        filename = str(document.get("file_name", ""))
        if filename.rsplit(".", 1)[-1].lower() not in ("csv", "xlsx") or any(
            char in filename for char in ("/", "\\", "\x00")
        ):
            await self.client.send(chat_id, "الملف لازم يكون CSV أو XLSX.")
            return
        if (
            not isinstance(document.get("file_size"), int)
            or not 0 < document["file_size"] <= MAX_BYTES
        ):
            await self.client.send(chat_id, "حجم الملف لازم يكون أقل من أو يساوي 5 ميجابايت.")
            return
        key = f"telegram:{update['update_id']}:{document.get('file_unique_id', '')}"
        async with self.services.factory() as uow:
            prior = await uow.submissions.get_reservation(learner.learner_id, key)
        if prior and prior.outcome:
            await self._result(chat_id, prior.outcome)
            return
        content = await self.client.download(str(document.get("file_id", "")))
        if not 0 < len(content) <= MAX_BYTES or len(content) != document["file_size"]:
            raise DomainError("artifact_integrity_failure", "File size mismatch")
        content_type = str(
            document.get("mime_type")
            or (
                "text/csv"
                if filename.lower().endswith(".csv")
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        )
        try:
            validate_content(filename, content_type, content)
        except DomainError:
            await self.client.send(
                chat_id, "محتوى الملف أو نوعه غير صالح. ارفع ملف CSV أو XLSX سليم."
            )
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
        if isinstance(result, ProcessingState):
            await self.client.send(chat_id, "التسليم قيد المراجعة، جرّب تاني بعد شوية.")
        else:
            await self._result(chat_id, result)

    async def _result(self, chat_id: int, result: SubmissionOutcome) -> None:
        decision = "التسليم مقبول" if result.evaluation.passed else "محتاج تعديل وإعادة تسليم"
        label = "إرشادات بديلة" if result.feedback.used_fallback else "ملاحظات المدرب"
        simulation = "تجربة ببيانات محاكاة\n" if self.services.simulated else ""
        await self.client.send(
            chat_id,
            f"{simulation}{decision} — {result.evaluation.score}/100\n{label}\n{result.feedback.feedback_text}\n/skills لعرض مهاراتك",
        )
