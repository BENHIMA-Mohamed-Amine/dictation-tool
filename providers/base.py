from abc import ABC, abstractmethod
from typing import Callable, List, Optional


class Provider(ABC):
    name: str
    streaming: bool

    @abstractmethod
    def configure(
        self,
        api_key: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        keyterms: Optional[List[str]] = None,
    ) -> None: ...

    @abstractmethod
    def start(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> None: ...

    @abstractmethod
    def feed_audio(self, chunk: bytes) -> None: ...

    @abstractmethod
    def stop(self) -> str: ...
