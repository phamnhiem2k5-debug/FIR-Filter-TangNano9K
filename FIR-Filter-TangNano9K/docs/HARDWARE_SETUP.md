# Hardware setup

## Included source

- [RTL](../fir-fpga-project/rtl/top_system.v): all supplied modules in one source file.
- [Physical constraints](../fir-fpga-project/constraints/fpga_1.cst): transcribed from the supplied CST text.
- [Example data](../fir-fpga-project/data/README.md): generated from the supplied app's default settings.

The original Gowin project file and original timing constraints were not supplied. The procedure below describes manual project reconstruction; it has not been executed in Gowin IDE during packaging.

## Recreate a Gowin project

1. Use Gowin IDE. The supplied report identifies version **V1.9.11.03 Education** and target **GW1NR-LV9QN88PC6/I5**, device version C. Match the target to the actual board before building.
2. Create a Verilog project and add `fir-fpga-project/rtl/top_system.v`.
3. Select `top_system` as the top-level module.
4. Add `fir-fpga-project/constraints/fpga_1.cst` as the physical constraint file.
5. Make `input_chirp.hex` and `input_dirac.hex` from `fir-fpga-project/data` available to the synthesis memory-initialization flow. The RTL uses literal relative names in `$readmemh`; ensure those names resolve in the tool's working/search directory. Copying the files into the working project directory is one approach. Check for missing-file warnings.
6. Configure and verify a 27 MHz system clock constraint using the actual project's timing setup. An original `.sdc` has not been reconstructed or claimed as supplied.
7. Synthesize, place-and-route, and inspect current timing and resource reports. The historical results included here are not substitutes for reports from a new build.
8. Program the board using the appropriate Gowin programming connection for the board.

`coeff.hex` is transferred through UART. It is not read as a coefficient ROM initialization file by this RTL. The app also exports `taps_config.vh`, but the supplied RTL does not include it: its 200-tap and 1000-sample dimensions are hardcoded.

## Pin mapping

Pin numbers below are **FPGA package pin numbers**, not GPIO header positions. Electrical settings are taken from the supplied CST.

| Signal | Direction | Package pin | I/O standard | Function |
|---|---|---:|---|---|
| `clk_27mhz` | Input | 52 | LVCMOS18 | System clock |
| `rst_n` | Input | 4 | LVCMOS18 | Active-low global reset |
| `key2` | Input | 3 | LVCMOS18 | Debounced mode toggle |
| `rx_pin` | Input | 18 | LVCMOS33 | Receive data into FPGA |
| `tx_pin` | Output | 17 | LVCMOS33 | Transmit data from FPGA |
| `led_done` | Output | 10 | LVCMOS18 | Low after all coefficients have been loaded |
| `led_mode` | Output | 14 | LVCMOS18 | `~mode`; low in Dirac mode |

## Run a chirp test

1. Build with the included chirp/Dirac ROM files and program the board.
2. Prepare a UART utility that sends binary coefficient words and captures raw result bytes. This utility was not supplied.
3. Assert and release `rst_n`. This clears the FIR history, coefficient-load state, FIFO, ROM controller, and mode to chirp.
4. Start collecting UART output before sending the final coefficient. The FPGA begins processing automatically when loading is complete.
5. Send all 200 coefficients from `coeff.hex` as **400 binary bytes**, high byte first per coefficient, at nominal 9600 baud, 8N1. Sending the ASCII characters in the HEX text file is not equivalent.
6. Receive **1000 × 6 = 6000 result bytes**. Group them into six-byte words, most significant byte first, and save one hexadecimal word per line as `output_chirp.hex`.
7. Upload the capture to the matching Streamlit design, or run the comparison helper documented in the root README.

Select Dirac mode by pressing `key2` once **after reset and before loading coefficients**, then repeat the capture process for `output_dirac.hex`. Keep the mode fixed throughout a run. A reset returns to chirp, so select Dirac again after each reset when needed.

## Coefficient reload and throughput

The loader accepts coefficients only while `coeffs_loaded == 0`. After 200 words it stays loaded until reset; there is no continuous hot-swap protocol in this source.

The ROM controller completes after 1000 samples and also requires reset to restart. Loading a new coefficient set does not require rebuilding the bitstream; changing ROM contents does.

At nominal 9600 baud with 8N1, 400 coefficient bytes require at least about 0.417 s and 6000 output bytes require at least 6.25 s. The UART transmitter's additional idle cycles and host handling can make the actual run longer. These estimates are transport calculations, not measured performance results.
