# Packaging checks

This file describes checks performed while assembling the repository. It does not replace FPGA synthesis, RTL simulation, or hardware validation.

## Checked

- Python syntax of the preserved app and the two added helper scripts.
- SHA-256 hashes for the four byte-preserved supplied source attachments.
- All 44 extracted images open as PNG files at their source dimensions.
- Local Markdown links resolve to packaged files.
- Example coefficients and chirp input exactly match the numeric generation block extracted from the supplied app with its default settings.
- Both 1000-sample software reference outputs match an independent scalar integer FIR calculation.
- HEX decoding handles negative numbers, signed 41-bit extrema, and both zero-padded and sign-extended six-byte representations.
- The comparison helper rejects wrong sample counts, unequal sample values, and malformed HEX input.
- No packaged file is empty.
- The final ZIP's CRC integrity and internal file paths are checked before delivery.

The case-result, architecture, and simulation-summary images were visually inspected. A contact sheet was used to review the other extracted figure occurrences. Images were not redrawn to improve or alter results.

## Not rerun here

- Streamlit UI startup and cloud deployment.
- Verilog compilation or original ISim simulation; the original testbench was not supplied.
- Gowin synthesis, place-and-route, timing closure, or bitstream generation.
- UART transfer or physical FPGA operation.
- Independent reconstruction of the report's measured MSE, Ep, or Es from raw hardware captures; those captures were not supplied.

The package preserves app and RTL code as supplied. Reported hardware results remain historical evidence from the supplied material. The included generated reference files are explicitly labeled as software references.
