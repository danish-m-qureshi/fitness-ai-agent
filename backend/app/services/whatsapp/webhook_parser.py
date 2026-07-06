from app.core.exceptions import AppException
from app.schemas.whatsapp import IncomingWhatsAppMessage, WhatsAppWebhookPayload


class WhatsAppWebhookParser:
    def parse(self, payload: WhatsAppWebhookPayload) -> IncomingWhatsAppMessage:
        raw_payload = payload.model_dump(by_alias=True)
        meta_message = self._parse_meta_payload(raw_payload)
        if meta_message is not None:
            return meta_message

        sender = payload.from_number or payload.sender or payload.phone_number
        if not sender:
            raise AppException(
                message="WhatsApp webhook payload must include a sender.",
                status_code=422,
                error_code="whatsapp_sender_required",
            )

        message_type = payload.message_type or payload.type or "text"
        text = payload.text
        if isinstance(text, dict):
            text = text.get("body")

        return IncomingWhatsAppMessage(
            sender=sender,
            user_id=payload.user_id,
            message_type=message_type,
            text=text,
            image_id=payload.image_id,
            image_url=payload.image_url,
            image_path=payload.image_path,
            raw_payload=raw_payload,
        )

    def _parse_meta_payload(
        self,
        raw_payload: dict,
    ) -> IncomingWhatsAppMessage | None:
        entries = raw_payload.get("entry")
        if not isinstance(entries, list) or not entries:
            return None

        try:
            value = entries[0]["changes"][0]["value"]
            message = value["messages"][0]
        except (KeyError, IndexError, TypeError):
            return None

        sender = message.get("from")
        message_type = message.get("type", "unknown")
        text = None
        image_id = None

        if message_type == "text":
            text_payload = message.get("text") or {}
            text = text_payload.get("body")
        elif message_type == "image":
            image_payload = message.get("image") or {}
            image_id = image_payload.get("id")

        if not sender:
            return None

        return IncomingWhatsAppMessage(
            sender=sender,
            message_type=message_type,
            text=text,
            image_id=image_id,
            raw_payload=raw_payload,
        )
