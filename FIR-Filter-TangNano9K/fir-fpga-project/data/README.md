# Reproducible example data

These files were generated during packaging using the default mathematical flow in the supplied `app.py`:

| Parameter | Value |
|---|---:|
| Fs | 8000 Hz |
| Passband edge | 1000 Hz |
| Stopband edge | 1400 Hz |
| Target attenuation | 60 dB |
| Active taps | 75 |
| Hardware taps | 200 |
| Input samples | 1000 per signal |
| Quantization scale | 32767 |

| File | Meaning |
|---|---|
| `coeff.hex` | 200 coefficient words, 16-bit two's complement; trailing coefficients are zero |
| `input_chirp.hex` | 1000 signed 16-bit chirp samples for ROM initialization |
| `input_dirac.hex` | Impulse of amplitude 32767 followed by 999 zeros |
| `reference/reference_chirp.hex` | Software reference: first 1000 raw 41-bit convolution outputs |
| `reference/reference_dirac.hex` | Software reference: first 1000 raw 41-bit convolution outputs |
| `design_parameters.json` | Parameters, generation versions, and numeric format |

Regenerate from the repository root:

```bash
python scripts/generate_vectors.py
```

The reference files are **not** FPGA captures. They may be used to exercise the file-upload UI, but that only tests the UI/reference path and must not be presented as hardware verification.

The RTL refers to ROM files by the literal names `input_chirp.hex` and `input_dirac.hex`. Configure the synthesis/simulation working directory or copy these files into it, and confirm the tool actually reads them.
