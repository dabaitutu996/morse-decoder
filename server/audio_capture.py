import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100
BLOCK_DURATION = 0.05  # 50ms
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)
BUFFER_SECONDS = 3.0
BUFFER_SIZE = int(SAMPLE_RATE * BUFFER_SECONDS)


class RingBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = np.zeros(capacity, dtype=np.float32)
        self.index = 0
        self.filled = False

    def extend(self, data: np.ndarray):
        data = np.asarray(data, dtype=np.float32)
        n = len(data)
        if n >= self.capacity:
            self.buffer[:] = data[-self.capacity:]
            self.index = 0
            self.filled = True
            return

        end = self.index + n
        if end <= self.capacity:
            self.buffer[self.index:end] = data
        else:
            first = self.capacity - self.index
            self.buffer[self.index:] = data[:first]
            self.buffer[:end - self.capacity] = data[first:]

        self.index = end % self.capacity
        if end >= self.capacity:
            self.filled = True

    def get_recent(self, seconds: float) -> np.ndarray:
        samples = int(seconds * SAMPLE_RATE)
        samples = min(samples, self.capacity)
        if not self.filled and samples > self.index:
            samples = self.index

        if self.index >= samples:
            return self.buffer[self.index - samples:self.index].copy()
        else:
            return np.concatenate([
                self.buffer[self.capacity - (samples - self.index):],
                self.buffer[:self.index]
            ])

    def snapshot(self) -> np.ndarray:
        if not self.filled:
            return self.buffer[:self.index].copy()
        return np.concatenate([self.buffer[self.index:], self.buffer[:self.index]])


def list_devices():
    devices = sd.query_devices()
    result = []
    for i, dev in enumerate(devices):
        result.append({
            "id": i,
            "name": dev["name"],
            "channels": dev["max_input_channels"],
            "sample_rate": dev["default_samplerate"],
            "is_loopback": "loopback" in dev["name"].lower() or "blackhole" in dev["name"].lower() or "vb-cable" in dev["name"].lower(),
        })
    return [d for d in result if d["channels"] > 0]


class AudioCapture:
    def __init__(self, callback, device_id=None):
        self.callback = callback
        self.device_id = device_id
        self.ring = RingBuffer(BUFFER_SIZE)
        self.stream = None

    def _on_audio(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        mono = indata[:, 0] if indata.shape[1] > 1 else indata[:, 0]
        self.ring.extend(mono)
        if self.callback:
            self.callback(mono.copy())

    def start(self):
        device_info = sd.query_devices(self.device_id, "input") if self.device_id is not None else None
        samplerate = int(device_info["default_samplerate"]) if device_info else SAMPLE_RATE
        channels = min(device_info["max_input_channels"], 1) if device_info else 1

        self.stream = sd.InputStream(
            device=self.device_id,
            channels=channels,
            samplerate=samplerate,
            blocksize=int(samplerate * BLOCK_DURATION),
            dtype=np.float32,
            callback=self._on_audio,
        )
        self.stream.start()
        return self

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    @property
    def is_active(self):
        return self.stream is not None and self.stream.active


if __name__ == "__main__":
    print("Available input devices:")
    for d in list_devices():
        print(f"  {d['id']}: {d['name']} (channels={d['channels']}, sr={d['sample_rate']}, loopback={d['is_loopback']})")
