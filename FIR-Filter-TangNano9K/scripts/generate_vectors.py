"""Generate reference data using the default design in the supplied Streamlit app.

Added during repository packaging. Outputs are software references, not FPGA captures.
Run from the repository root: python scripts/generate_vectors.py
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import signal


ROOT = Path(__file__).resolve().parents[1]


def write_hex(path, values, bits):
    mask = (1 << bits) - 1
    digits = (bits + 3) // 4
    path.write_text(
        "".join(f"{int(v) & mask:0{digits}x}\n" for v in values), encoding="ascii"
    )


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    reference = output / "reference"
    reference.mkdir(exist_ok=True)
    fs, fp, fst, attenuation = 8000, 1000, 1400, 60
    capacity, samples, scale = 200, 1000, 32767
    n, beta = signal.kaiserord(attenuation, (fst - fp) / (fs / 2))
    if n % 2 == 0:
        n += 1
    if n > capacity:
        raise ValueError("Filter exceeds the fixed 200-tap hardware capacity")
    h = signal.firwin(n, (fp + fst) / 2, window=("kaiser", beta), fs=fs)
    hq = np.clip(np.round(h * scale), -scale, scale).astype(np.int64)
    padded = np.zeros(capacity, dtype=np.int64)
    padded[:n] = hq
    t = np.linspace(0, samples / fs, samples, endpoint=False)
    raw = 0.5 * signal.chirp(t, f0=0, f1=fs / 2, t1=t[-1], method="linear")
    chirp = np.clip(np.round(raw * scale), -scale, scale).astype(np.int64)
    impulse = np.zeros(samples, dtype=np.int64)
    impulse[0] = scale
    write_hex(output / "coeff.hex", padded, 16)
    write_hex(output / "input_chirp.hex", chirp, 16)
    write_hex(output / "input_dirac.hex", impulse, 16)
    for label, x in (("chirp", chirp), ("dirac", impulse)):
        y = np.convolve(x, padded)[:samples]
        if np.any(y < -(1 << 40)) or np.any(y >= (1 << 40)):
            raise ValueError("Reference result exceeds signed 41-bit range")
        write_hex(reference / f"reference_{label}.hex", y, 41)
    metadata = {
        "origin": "Software reference generated from the supplied app.py default design",
        "is_hardware_capture": False,
        "fs_hz": fs,
        "passband_edge_hz": fp,
        "stopband_edge_hz": fst,
        "target_attenuation_db": attenuation,
        "active_taps": int(n),
        "hardware_taps": capacity,
        "kaiser_beta": float(beta),
        "sample_count": samples,
        "coefficient_and_input_scale": scale,
        "app_output_display_divisor": 1 << 30,
        "reference_encoding": "One 41-bit two's-complement result per hex line",
        "numpy_version": np.__version__,
        "scipy_version": __import__("scipy").__version__,
    }
    (output / "design_parameters.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {n} active taps padded to {capacity}; {samples} samples per input.")
    print("Outputs are software references, not measured FPGA outputs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "fir-fpga-project" / "data")
    generate(parser.parse_args().output)
