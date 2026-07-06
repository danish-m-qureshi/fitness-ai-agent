from abc import ABC, abstractmethod


class WhatsAppProvider(ABC):
    name: str

    @abstractmethod
    async def send_text(self, to: str, message: str) -> None:
        pass

    @abstractmethod
    async def send_image(
        self,
        to: str,
        image_path: str,
        caption: str | None = None,
    ) -> None:
        pass
