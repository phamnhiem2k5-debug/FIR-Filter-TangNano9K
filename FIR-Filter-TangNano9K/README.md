# Reconfigurable FIR Filter on Tang Nano 9K

**Verilog HDL · Sequential MAC · UART · Python · Streamlit**

A configurable low-pass FIR filter implemented on the **Sipeed Tang Nano 9K FPGA**. The project combines a fixed 200-tap hardware datapath with UART coefficient loading and a Python/Streamlit application for filter design, test-vector generation, and output verification.

## Interactive application

### [Open the FIR Design and Verification App](https://fir-filter-tangnano9k-c9gtlotqpafsu5vqvetx56.streamlit.app/)

Use the web application to design a Kaiser-window FIR filter, inspect its frequency response, generate input and coefficient files, and upload FPGA output files for comparison.

**Documentation:** [Hardware setup](docs/HARDWARE_SETUP.md) · [UART protocol](docs/UART_PROTOCOL.md) · [Result gallery](docs/RESULTS_GALLERY.md) · [Project report](reports/project_report.pdf) · [Hướng dẫn tiếng Việt](HUONG_DAN_UPLOAD.md)

![FPGA and Python comparison for the 75-tap configuration](docs/images/case2_results.png)

*75-tap configuration: waveform comparison, group delay, and frequency response. Image extracted from Figure 4.21 of the project report.*

## Features

- **200-tap FIR core** using a sequential multiply-accumulate architecture.
- **16-bit signed inputs and coefficients**, with a 41-bit accumulated output.
- **UART coefficient loading** after reset, without rebuilding or reprogramming the bitstream.
- **Chirp and Dirac impulse test signals** stored in two 1000-sample ROMs.
- **1024 × 41-bit FIFO** to buffer results before UART transmission.
- **Python reference model** for output comparison and error analysis.
- **Streamlit interface** for filter design, HEX export, result visualization, and CSV export.

## System architecture

![FIR system architecture](docs/images/system_architecture.png)

The system has two main paths:

| Path | Processing flow |
|---|---|
| Coefficient loading | PC UART utility → UART RX → Byte Packer → Coefficient Loader → coefficient memory |
| Filtering and output | Input ROM → ROM Controller → FIR Core → FIFO → Byte Unpacker → UART TX → PC capture utility |

The FIR core reuses one MAC datapath across **200 iterations per output sample**. Filters with fewer active coefficients are padded with zeros to the fixed hardware length; the number of MAC iterations remains 200.

The Streamlit application exchanges data through files. UART transfer and capture require a separate utility; serial-port communication is not implemented in the supplied `app.py`.

## Design specifications

| Parameter | Value |
|---|---|
| Development board | Sipeed Tang Nano 9K |
| FPGA target | GW1NR-LV9QN88PC6/I5 |
| System clock | 27 MHz |
| Hardware filter length | 200 taps |
| Input samples | Signed 16-bit |
| Filter coefficients | Signed 16-bit, Q15-style quantization |
| Accumulator and output | Signed 41-bit raw sum of products |
| UART configuration | Nominal 9600 baud, 8N1 |
| Coefficient payload | 200 words, two bytes per word, high byte first |
| Result payload | Six bytes per sample, high byte first |
| Test signal memory | 1000 chirp samples and 1000 Dirac samples |
| Output FIFO | 1024 × 41 bits |

The app quantizes coefficients and input samples using a scale of **32767**. The RTL outputs the raw accumulated sum; the app decodes the signed 41-bit result and divides by **2^30** for display and comparison. See [numeric format and UART details](docs/UART_PROTOCOL.md).

## Run locally

From the repository root:

```bash
python -m pip install -r fir-fpga-project/requirements.txt
python -m streamlit run fir-fpga-project/app.py
```

The application provides four tabs:

1. **Design** — enter filter specifications and calculate Kaiser coefficients.
2. **Python simulation** — inspect the filter frequency response.
3. **Test data and export** — generate chirp/Dirac inputs and download HEX files.
4. **Verification** — upload FPGA outputs, compare waveforms, inspect errors, and export CSV data.

### Streamlit Community Cloud configuration

| Setting | Value |
|---|---|
| Repository | `phamnhiem2k5-debug/fir-filter-tangnano9k` |
| Branch | `main` |
| Main file path | `fir-fpga-project/app.py` |
| Python version | `3.12` |
| Dependency file | `fir-fpga-project/requirements.txt` |

Python 3.12 is compatible with the `numpy==1.26.4` and `scipy==1.13.1` versions used in the deployment configuration. Select it in **Advanced settings** when deploying with those pins.

## Example data and verification

The included example uses **Fs = 8000 Hz**, **Fp = 1000 Hz**, **Fstop = 1400 Hz**, and a **60 dB target attenuation**. Its 75 active coefficients are padded to 200.

Regenerate the example files:

```bash
python scripts/generate_vectors.py
```

This produces coefficient/input HEX files and software reference outputs in [the data directory](fir-fpga-project/data/README.md). Files named `reference_*.hex` are calculated references, not FPGA captures.

To verify a real chirp capture with one output word per HEX line:

```bash
python scripts/compare_hex.py captures/output_chirp.hex fir-fpga-project/data/reference/reference_chirp.hex
```

The helper checks every signed integer output and requires matching sample counts. Capture data using the same coefficients and ROM inputs as the reference.

## Verification results

The project report documents **Xilinx ISE/ISim RTL simulation** and **Python/Streamlit system-level verification**. The following values are transcribed from its reported test results.

| Active taps | Hardware taps | MSE | Maximum absolute error | Passband ripple Ep | Stopband leakage Es |
|---:|---:|---:|---:|---:|---:|
| 19 | 200 | 0 | 0 | 0.013787 | 0.011013 |
| 75 | 200 | 0 | 0 | 0.001092 | 0.001099 |
| 175 | 200 | 0 | 0 | 0.000409 | 0.000452 |

Source: Table 4.10, PDF page 67 of the [project report](reports/project_report.pdf). A [CSV version](reports/reported_filter_results.csv) is included.

Zero error applies to the reported comparisons against the quantized reference for those test cases. Quantization error relative to an ideal floating-point filter is a separate measurement.

![RTL integration test summary](docs/images/simulation_summary.png)

*Figure 4.12: the report's integration simulation loads 200 coefficients, generates 10 results, and transmits 60 bytes with zero reported unit/system errors. This 10-sample test is separate from the deployment RTL's 1000-sample ROM configuration.*

The [result gallery](docs/RESULTS_GALLERY.md) contains **44 extracted report images**, including architecture diagrams, RTL waveforms, application screens, and all three filter configurations.

## FPGA implementation results

| Resource | Usage | Reported utilization |
|---|---|---:|
| Logic | 2063 / 8640 | 24% |
| Registers | 3556 / 6693 | 54% |
| CLS | 2805 / 4320 | 65% |
| I/O ports | 7 / 71 | 10% |
| BSRAM | 4 SDPB + 2 pROM | 24% |
| DSP | 1 MULTADDALU18X18 | 10% |

Counts and percentages follow the [supplied Gowin resource table](reports/gowin_resource_usage.txt), including its DSP accounting.

The [Gowin timing excerpt](reports/gowin_timing_report.txt) reports:

- **Operating clock:** 27 MHz.
- **Estimated Fmax:** 39.625 MHz.
- **Setup/hold violated endpoints:** 0 / 0 for the analyzed paths.

Fmax is a tool-reported estimate rather than a demonstrated board frequency. The excerpt lists `Timing Constraint File ---`, so complete external I/O timing coverage is not established by these results.

## Repository structure

```text
FIR-Filter-TangNano9K/
├── README.md
├── HUONG_DAN_UPLOAD.md
├── .gitignore
├── fir-fpga-project/
│   ├── app.py
│   ├── requirements.txt
│   ├── rtl/top_system.v
│   ├── constraints/fpga_1.cst
│   └── data/
├── scripts/
│   ├── generate_vectors.py
│   └── compare_hex.py
├── sim/README.md
├── docs/
│   ├── HARDWARE_SETUP.md
│   ├── UART_PROTOCOL.md
│   ├── RESULTS_GALLERY.md
│   ├── SOURCE_NOTES.md
│   └── images/
└── reports/
    ├── project_report.pdf
    ├── gowin_resource_usage.txt
    ├── gowin_timing_report.txt
    └── reported_filter_results.csv
```

## Current scope

- Reset is required before loading another coefficient set or restarting a completed ROM run.
- `key2` toggles chirp/Dirac mode on each debounced press. Reset selects chirp.
- Input samples are ROM-based. Changing ROM data requires rebuilding the FPGA image; changing coefficients does not.
- The original Gowin `.gprj`, timing `.sdc`, testbench, UART utility, raw hardware captures, and bitstream are not included.

See [hardware setup](docs/HARDWARE_SETUP.md), [source notes](docs/SOURCE_NOTES.md), and [packaging checks](reports/PACKAGING_CHECKS.md) for reconstruction steps and the scope of the included evidence.

## Contributors

The original project report credits **Đinh Thị Kiều My** and **Phạm Văn Nhiệm**, supervised by **ThS. Nguyễn Văn Phúc**.

The [Vietnamese project report](reports/project_report.pdf) is included unchanged. No open-source license has been assigned.
