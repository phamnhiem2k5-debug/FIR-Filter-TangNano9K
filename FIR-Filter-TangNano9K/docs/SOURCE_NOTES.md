# Source provenance and known differences

## Preserved material

| Supplied material | Packaged path | Treatment |
|---|---|---|
| Python text attachment | `fir-fpga-project/app.py` | Copied byte for byte |
| Verilog text attachment | `fir-fpga-project/rtl/top_system.v` | Copied byte for byte; modules kept together |
| Timing text attachment | `reports/gowin_timing_report.txt` | Copied byte for byte; supplied excerpt only |
| Vietnamese report PDF | `reports/project_report.pdf` | Copied byte for byte |
| Physical constraint text in chat | `fir-fpga-project/constraints/fpga_1.cst` | Transcribed with the same statements |
| Resource usage table in chat | `reports/gowin_resource_usage.txt` | Transcribed; percentages retained |
| Embedded report figures | `docs/images/*.png` | Extracted at native resolution, with page mappings |

The source hashes are recorded in `reports/source_manifest.json`. Figures remain part of the original authors' report; extracting them does not assign new ownership or a new license.

## Added during packaging

- README, Vietnamese upload guide, hardware and protocol documentation.
- Unpinned `requirements.txt`, inferred from imports in the supplied app.
- `.gitignore`.
- `scripts/generate_vectors.py`: reproduces the app's default 75-tap design and writes example ROM/coefficient/reference files.
- `scripts/compare_hex.py`: decodes signed 41-bit HEX words and compares captures against references.
- CSV transcription of the report's result table and image/source manifests.

Neither helper script is the original UART utility or original testbench. No new hardware measurements, FPGA bitstream, or captured FPGA output is fabricated.

## Differences clarified in the documentation

1. **Simulator name:** the supplied report's simulation chapter, tool table, and summary image identify Xilinx ISE/ISim. Earlier CV text mentioned Vivado/XSim and another report sentence mentions Vivado. This repository follows the main documented evidence; the testbench/tool files are needed to settle all version details.
2. **Fixed loop length:** the RTL executes 200 MAC iterations for every sample, even when the active coefficient sequence is shorter. Shortening the coefficient sequence does not shorten this source's loop.
3. **Coefficient reload:** `coeffs_loaded` remains set until reset, and `rom_controller.done` also remains set until reset. There is no unrestricted in-run coefficient update protocol.
4. **Signed transport:** the supplied RTL zero-pads the 41-bit output to 48 bits. The supplied Python masks to 41 bits and sign-decodes it. A report description of 48-bit sign extension differs from this implementation.
5. **Application scope:** this Streamlit app exports files and imports HEX captures. It contains no direct serial-port transfer code.
6. **Mode button:** `key2` toggles mode per debounced press. Its held/released state is not a direct Dirac/chirp selector. Mode defaults to chirp on reset.
7. **Configuration header:** the app exports `taps_config.vh`, but this RTL does not include it. Dimensions are hardcoded; the helper does not imply the header controls this RTL.
8. **Simulation data length:** report simulation evidence uses 10 samples; the supplied deployment RTL uses two 1000-sample ROMs.
9. **Report figures:** Figures 4.5 and 4.6 reuse the same embedded raster in the PDF. Both occurrences are retained and labeled as such.
10. **Timing evidence:** the timing attachment is an excerpt dated 17 September 2026, with `Timing Constraint File ---`. Its Fmax is reported evidence for that run, not a fresh timing validation of this package or complete external I/O coverage.
11. **Numeric scale:** the app quantizes with 32767 and displays accumulated results divided by 2^30. Documentation states the actual code behavior instead of assuming all operations use 32768 normalization.
12. **Report precision:** the app formats scalar results for display. The report's displayed zero MSE/max error is preserved as reported; raw capture files were not supplied for independent confirmation.

## Not supplied

- Original Gowin `.gprj` project and timing `.sdc`.
- Original RTL testbench and simulator project/scripts.
- Original serial transfer/capture utility.
- Original HEX input/output captures used for the three reported cases.
- Original bitstream and build environment lockfile.

The report is included unchanged, including its existing formatting, bookmarks, and technical inconsistencies. Corrections above apply to the repository documentation; they do not silently rewrite the source report or source code.
