import numpy as np
from scipy.signal import butter, lfilter
from typing import Callable, Optional

SAMPLE_RATE = 44100

MORSE_TABLE = {
    ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
    "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
    "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
    ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
    "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
    "--..": "Z", "-----": "0", ".----": "1", "..---": "2",
    "...--": "3", "....-": "4", ".....": "5", "-....": "6",
    "--...": "7", "---..": "8", "----.": "9", ".-.-.-": ".",
    "--..--": ",", "..--..": "?", "-..-.": "/", "-....-": "-",
    "-.--.": "(", "-.--.-": ")", ".----.": "'", "---...": ":",
    "-.-.-.": ";", "-...-": "=", ".-.-.": "+", "..--.-": "_",
}


class ButterworthFilter:
    def __init__(self, lowcut, highcut, order=4):
        nyq = SAMPLE_RATE / 2
        low = max(lowcut / nyq, 0.001)
        high = min(highcut / nyq, 0.999)
        self.b, self.a = butter(order, [low, high], btype="band")
        self.zi = np.zeros(max(len(self.a), len(self.b)) - 1)

    def process(self, x: np.ndarray) -> np.ndarray:
        y, self.zi = lfilter(self.b, self.a, x, zi=self.zi)
        return y


class EnvelopeDetector:
    def __init__(self, cutoff=30.0):
        nyq = SAMPLE_RATE / 2
        self.b, self.a = butter(1, cutoff / nyq, btype="low")
        self.zi = np.zeros(max(len(self.a), len(self.b)) - 1)

    def process(self, x: np.ndarray) -> np.ndarray:
        rectified = np.abs(x)
        y, self.zi = lfilter(self.b, self.a, rectified, zi=self.zi)
        return y


class MorseDecoder:
    def __init__(
        self,
        frequency: float = 800.0,
        wpm: Optional[float] = 20.0,
        gain: float = 1.0,
        squelch: float = 0.08,
        on_letter: Optional[Callable[[str], None]] = None,
        on_word: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.frequency = frequency
        self.target_wpm = wpm
        self.gain = gain
        self.squelch = squelch
        self.on_letter = on_letter
        self.on_word = on_word
        self.on_error = on_error

        # Wide bandpass: covers 300-1500Hz, matches most Morse tones
        self.bandpass = ButterworthFilter(300, 1500, order=4)
        self.envelope = EnvelopeDetector(cutoff=30.0)

        self.state = False  # current on/off state
        self.signal_level = 0.0
        self.threshold = squelch
        self.noise_floor = 0.0
        self.signal_peak = 0.0

        self.dit_length = 1.2 / wpm if wpm else None
        self.samples_processed = 0
        self.last_edge_time = 0.0
        self.current_code = ""
        self.current_word = ""

    def set_frequency(self, frequency: float):
        self.frequency = frequency
        # Wide bandpass covers all common Morse tones
        pass

    def set_gain(self, gain: float):
        self.gain = max(0.1, min(10.0, gain))

    def set_wpm(self, wpm: float):
        if wpm <= 0:
            return
        self.target_wpm = wpm
        self.dit_length = 1.2 / wpm

    def _update_level(self, envelope: np.ndarray):
        peak = float(np.max(envelope)) if len(envelope) > 0 else 0.0
        mean = float(np.mean(envelope)) if len(envelope) > 0 else 0.0

        # Apply gain
        peak *= self.gain
        mean *= self.gain

        # Track signal peak (fast attack, slow decay)
        if peak > self.signal_peak:
            self.signal_peak = 0.9 * self.signal_peak + 0.1 * peak
        else:
            self.signal_peak = 0.9995 * self.signal_peak + 0.0005 * peak

        # Noise floor: follow low values
        if mean < self.signal_peak * 0.3:
            self.noise_floor = 0.98 * self.noise_floor + 0.02 * mean
        else:
            self.noise_floor = 0.999 * self.noise_floor

        # Ensure minimum signal peak to prevent false triggers on noise
        self.signal_peak = max(self.signal_peak, self.noise_floor * 2 + 0.01)

        # Threshold between noise and signal
        self.threshold = self.noise_floor + 0.30 * (self.signal_peak - self.noise_floor) + 0.005
        self.threshold = max(self.threshold, self.noise_floor * 2 + 0.002)
        self.signal_level = min(peak / (self.signal_peak + 1e-9), 1.0)

    def _classify_element(self, duration: float) -> Optional[str]:
        if self.dit_length is None or self.dit_length <= 0:
            return "." if duration < 0.12 else "-"
        ratio = duration / self.dit_length
        if ratio < 1.7:
            return "."
        return "-"

    def _classify_gap(self, duration: float) -> Optional[str]:
        if self.dit_length is None or self.dit_length <= 0:
            if duration > 0.30:
                return "word"
            elif duration > 0.10:
                return "letter"
            return None
        ratio = duration / self.dit_length
        if ratio > 5.0:
            return "word"
        elif ratio > 1.7:
            return "letter"
        return None

    def feed_audio(self, samples: np.ndarray):
        samples = np.asarray(samples, dtype=np.float32)
        n = len(samples)

        chunk_start_time = self.samples_processed / SAMPLE_RATE
        times = chunk_start_time + np.arange(n) / SAMPLE_RATE

        filtered = self.bandpass.process(samples)
        envelope = self.envelope.process(filtered)
        self._update_level(envelope)

        high = self.threshold * 1.15
        low = self.threshold * 0.85

        # Debounce: ignore transitions shorter than this
        MIN_ELEMENT_MS = 0.030  # 30ms
        MAX_CODE_LEN = 8        # max symbols per letter

        for i, (t, val) in enumerate(zip(times, envelope)):
            if not self.state and val > high:
                # Potential rising edge
                gap = t - self.last_edge_time
                if gap < MIN_ELEMENT_MS:
                    continue  # too soon, ignore
                gap_type = self._classify_gap(gap)
                if gap_type == "letter" and self.current_code:
                    self._finish_letter()
                elif gap_type == "word" and (self.current_code or self.current_word):
                    if self.current_code:
                        self._finish_letter()
                    self._finish_word()
                self.state = True
                self.last_edge_time = t
            elif self.state and val < low:
                # Potential falling edge
                duration = t - self.last_edge_time
                if duration < MIN_ELEMENT_MS:
                    continue  # too short to be a valid element, skip
                symbol = self._classify_element(duration)
                if symbol:
                    self.current_code += symbol
                    if len(self.current_code) > MAX_CODE_LEN:
                        if self.on_error:
                            self.on_error(f"Code too long, reset: {self.current_code}")
                        self.current_code = ""
                self.state = False
                self.last_edge_time = t

        self.samples_processed += n

    def _finish_letter(self):
        code = self.current_code
        self.current_code = ""
        letter = MORSE_TABLE.get(code)
        if letter:
            self.current_word += letter
            if self.on_letter:
                self.on_letter(letter)
        else:
            if self.on_error:
                self.on_error(f"Unknown code: {code}")

    def _finish_word(self):
        if self.on_word:
            self.on_word()

    def flush(self):
        if self.current_code:
            self._finish_letter()
        if self.current_word:
            self._finish_word()

    @property
    def current_wpm(self) -> float:
        return self.target_wpm or 0.0


if __name__ == "__main__":
    import math

    def generate_word(word_code, wpm=20, freq=800):
        dit_len = 1.2 / wpm
        parts = []
        for i, letter_code in enumerate(word_code.split()):
            if i > 0:
                parts.extend(np.zeros(int(SAMPLE_RATE * dit_len * 7)))  # standard word gap: 7 dit lengths
            for symbol in letter_code:
                duration = dit_len * (3 if symbol == "-" else 1)
                t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
                tone = 0.5 * np.sin(2 * np.pi * freq * t)
                parts.extend(tone)
                parts.extend(np.zeros(int(SAMPLE_RATE * dit_len)))
        return np.array(parts, dtype=np.float32)

    tests = [
        ("-.-. --.- -.-.", "CQC"),
        ("-.-. --.-", "CQ"),
        (".- .--.", "AP"),
        ("... --- ...", "SOS"),
        ("-.-. --.- -.. .", "CQDE"),
        (".- .-. .-.", "ARR"),
        ("-.-. --.- -.. . / .-- .... .- -", "CQDE WHAT"),
    ]

    for code, expected in tests:
        decoded = []
        words = []
        decoder = MorseDecoder(
            frequency=800,
            wpm=20,
            on_letter=lambda l, d=decoded: d.append(l),
            on_word=lambda d=words: d.append(" "),
        )
        audio = generate_word(code, wpm=20, freq=800)
        chunk_size = int(SAMPLE_RATE * 0.05)
        for i in range(0, len(audio), chunk_size):
            decoder.feed_audio(audio[i:i+chunk_size])
        decoder.flush()
        result = "".join(decoded) + ("".join(words) if words else "")
        result = result.strip()
        print(f"{code:40} -> {result:15} (expected {expected}) {'OK' if result == expected else 'FAIL'}")
