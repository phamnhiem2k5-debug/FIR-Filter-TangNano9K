# Reconfigurable FIR Filter on Tang Nano 9K

**Verilog RTL · Sequential MAC · UART coefficient loading · Python / Streamlit verification**

A low-pass FIR filter implemented on the Sipeed Tang Nano 9K FPGA. The design combines a fixed 200-tap hardware datapath, UART-based coefficient loading, ROM-based input signals, and a Streamlit application for filter design and output analysis.

**Start here:** [Chạy và upload bằng tiếng Việt](HUONG_DAN_UPLOAD.md) · [Hardware setup](docs/HARDWARE_SETUP.md) · [Result gallery](docs/RESULTS_GALLERY.md) · [Project report](reports/project_report.pdf)

![Reported 75-tap verification results](docs/images/case2_results.png)

*Case 2 results extracted from the project report, Figure 4.21. This is reported evidence, not a new FPGA measurement performed while packaging this repository.*

## Highlights

- Implements a sequential multiply-accumulate datapath for 200 hardware taps.
- Accepts signed 16-bit samples and signed 16-bit coefficients.
- Accumulates FIR results into a signed 41-bit word.
- Loads 200 coefficients over UART after reset, without rebuilding the bitstream.
- Selects chirp or Dirac impulse input data from two 1000-sample ROMs.
- Buffers output in a 1024 × 41-bit FIFO before UART transmission.
- Provides a Streamlit interface for Kaiser-window design, HEX export, and file-based output verification.

## System architecture

![System architecture from the report](docs/images/system_architecture.png)

The coefficient path is **PC UART utility → UART RX → Byte Packer → Coefficient Loader → coefficient memory**.

The filtering path is **input ROM → FIR core → FIFO → output byte packer → UART TX → PC capture utility**.

The Streamlit app designs filters and processes uploaded result files. It does **not** directly open a serial port; the original UART transfer/capture utility was not supplied.

![Sequential MAC datapath](docs/images/fir_mac_architecture.png)

The RTL always executes 200 MAC iterations per output sample. Shorter filters are represented by zero-padding coefficients to 200 entries; they do not shorten the MAC loop in this version.

## Specifications

| Parameter | Implementation |
|---|---|
| Board / FPGA | Sipeed Tang Nano 9K / GW1NR-9 |
| Supplied target part | GW1NR-LV9QN88PC6/I5 |
| System clock | 27 MHz |
| Hardware filter length | Fixed 200 taps |
| Input | Signed 16-bit samples |
| Coefficients | Signed 16-bit, Q15-style quantization |
| Accumulator / output | Signed 41-bit raw sum of products |
| UART | Nominal 9600 baud, 8 data bits, no parity, 1 stop bit |
| Coefficient order | Two bytes per coefficient, high byte first |
| Result order | Six bytes per result, high byte first |
| Input ROMs | Chirp and Dirac impulse, 1000 samples each |
| FIFO | 1024 words × 41 bits |

The supplied app quantizes coefficients and input samples using a scale of **32767**. The RTL does not shift the accumulated result back to 16 bits. The app decodes signed 41-bit results and divides by **2^30** for display and comparison. See [numeric and UART details](docs/UART_PROTOCOL.md).

## Run the Streamlit application

From the repository root, with Python available:

```bash
python -m pip install -r fir-fpga-project/requirements.txt
python -m streamlit run fir-fpga-project/app.py
```

The four app tabs support:

1. Low-pass filter specifications and Kaiser-window design.
2. Python frequency-response visualization.
3. Export of coefficients, chirp/Dirac inputs, and a configuration header.
4. Upload of FPGA HEX outputs, waveform/error analysis, and CSV export.

For Streamlit Community Cloud, select branch `main` and entrypoint **`fir-fpga-project/app.py`**. Dependencies are in the adjacent `requirements.txt`.

## Included example data

The [data directory](fir-fpga-project/data/README.md) contains a reproducible default design: Fs = 8000 Hz, Fp = 1000 Hz, Fstop = 1400 Hz, target attenuation = 60 dB, 75 active taps padded to 200.

```bash
python scripts/generate_vectors.py
```

The script regenerates `coeff.hex`, `input_chirp.hex`, `input_dirac.hex`, and **software reference** outputs. The reference files are not captured FPGA results.

To check a real chirp capture containing one output word per line:

```bash
python scripts/compare_hex.py captures/output_chirp.hex fir-fpga-project/data/reference/reference_chirp.hex
```

The command requires equal sample counts and checks every raw signed integer result. Use the matching coefficients and ROM data when collecting captures.

## Reported verification results

The supplied report documents RTL simulation using **Xilinx ISE/ISim** and system-level comparisons using Python/Streamlit. The original testbench and raw hardware output files were not included in the supplied source material.

| Case | Active coefficient length | Hardware length | Reported MSE | Reported max error | Reported Ep | Reported Es |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 19 | 200 | 0 | 0 | 0.013787 | 0.011013 |
| 2 | 75 | 200 | 0 | 0 | 0.001092 | 0.001099 |
| 3 | 175 | 200 | 0 | 0 | 0.000409 | 0.000452 |

Source: Table 4.10, PDF page 67 of the [report](reports/project_report.pdf). [CSV copy](reports/reported_filter_results.csv).

Zero error refers to the reported comparisons with the quantized reference for those cases. It does not establish zero error relative to an ideal floating-point filter for all inputs.

![Reported RTL simulation summary](docs/images/simulation_summary.png)

*Figure 4.12: the report's 10-sample integration test summary. The supplied deployment RTL uses 1000-sample ROMs; the report's testbench configuration is a separate scenario.*

![FIR waveform from the report](docs/images/wave_fir_a.png)

All architecture, app, waveform, and case-result images are available in the [44-image gallery](docs/RESULTS_GALLERY.md), with source page mappings.

## Reported FPGA implementation results

| Resource | Usage | Utilization reported by Gowin |
|---|---|---:|
| Logic | 2063 / 8640 | 24% |
| Registers | 3556 / 6693 | 54% |
| CLS | 2805 / 4320 | 65% |
| I/O ports | 7 / 71 | 10% |
| BSRAM | 4 SDPB + 2 pROM | 24% |
| DSP | 1 MULTADDALU18X18 | 10% |

The DSP percentage is retained exactly as provided; it describes the tool's resource accounting. Resource categories are not additive. [Full supplied resource table](reports/gowin_resource_usage.txt).

The supplied Gowin timing excerpt reports a **27 MHz clock**, **39.625 MHz Fmax**, and **zero setup/hold violated endpoints** in that analysis. Fmax is a timing-analysis estimate, not a demonstrated board operating frequency. The report lists `Timing Constraint File ---`; these values do not establish complete external I/O timing coverage. [Supplied timing excerpt](reports/gowin_timing_report.txt).

## Repository layout

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
│   └── data/                    # Inputs, coefficients, and software references
├── scripts/                     # Added data-generation and comparison helpers
├── sim/README.md                # Simulation evidence and missing testbench details
├── docs/                        # Hardware guide, protocol, provenance, and images
└── reports/                     # Original PDF, resource table, timing excerpt, CSV
```

## Current scope and reproducibility

- Coefficient loading is allowed once per reset. Reset before loading another set.
- Input is read from ROM, rather than an ADC or a streaming input interface.
- `key2` toggles signal mode on each debounced press. Reset defaults to chirp mode.
- Updating coefficients does not require rebuilding the FPGA image. Updating ROM input data does.
- The original `.gprj`, timing `.sdc`, testbench, UART utility, raw captures, and bitstream were not supplied. This package preserves the available source and documents how to recreate the project manually; it is not an exact archive of the original build environment.
- Python dependencies are unpinned because the original version list was not supplied.

Read [source provenance and known differences](docs/SOURCE_NOTES.md) and [packaging checks](reports/PACKAGING_CHECKS.md) before interpreting reported results as newly reproduced results.

## Contributors and report

The supplied report lists **Đinh Thị Kiều My** and **Phạm Văn Nhiệm** as the student authors, supervised by **ThS. Nguyễn Văn Phúc**. It does not specify individual ownership of each module.

The [original Vietnamese project report](reports/project_report.pdf) is included unchanged. No open-source license has been selected on behalf of its authors.
