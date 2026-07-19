from typing import Callable, Optional

import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # bytes per sample (int16)


class AudioRecorder:
    def __init__(self) -> None:
        self._stream: Optional[sd.RawInputStream] = None

    def start(self, on_chunk: Callable[[bytes], None]) -> None:
        def callback(indata, frames, time, status) -> None:
            on_chunk(bytes(indata))

        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
