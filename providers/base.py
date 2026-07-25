from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple


# Offered by every provider that takes plain ISO-639-1 language codes (Groq,
# Soniox). Deliberately short — a handful of useful languages plus auto-detect,
# not an exhaustive list of everything the models can do.
AUTO_DETECT = ("Auto-detect", None)
ISO_639_1_LANGUAGES: List[Tuple[str, Optional[str]]] = [
    AUTO_DETECT,
    ("English", "en"),
    ("French", "fr"),
    ("Arabic", "ar"),
    ("Spanish", "es"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
]


class Provider(ABC):
    name: str
    streaming: bool

    # How the provider is written in the UI (tray submenu, settings tab).
    # `name` is the config/registry key and stays lowercase; this is the human
    # spelling, so "nvidia" doesn't render as "Nvidia".
    display_name: str

    # What the settings window offers for this provider. Declared here so the
    # window can build a tab for any registered provider by iterating PROVIDERS,
    # instead of branching on the provider name — adding a provider stays a
    # providers/-only change.
    #
    # MODELS: selectable model ids; empty means the provider exposes no choice.
    # LANGUAGES: (label, code) pairs; a code of None means auto-detect, i.e. send
    # no language hint at all. Providers whose API requires an explicit language
    # simply don't offer a None entry.
    # MODEL_LABEL: the model this provider transcribes with, shown read-only in
    # settings. A single string, not a list, because each provider currently
    # offers exactly one model worth using — a one-entry dropdown is dead UI.
    # If a provider ever gains a real choice, this becomes a list and the label
    # becomes a dropdown.
    MODEL_LABEL: str = ""
    LANGUAGES: List[Tuple[str, Optional[str]]] = []

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
