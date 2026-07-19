from typing import Dict, Type

from providers.base import Provider
from providers.groq import GroqProvider
from providers.nvidia import NvidiaProvider
from providers.soniox import SonioxProvider

PROVIDERS: Dict[str, Type[Provider]] = {
    "groq": GroqProvider,
    "soniox": SonioxProvider,
    "nvidia": NvidiaProvider,
}
