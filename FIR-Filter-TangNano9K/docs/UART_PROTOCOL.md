# UART and numeric format

This document describes the supplied RTL and Python decoder. It is not a newly introduced framing protocol.

## Physical UART settings

- System clock: 27 MHz.
- UART: nominal 9600 baud, 8 data bits, no parity, one stop bit, idle high.
- Data bits within each UART byte are sent least significant bit first.
- Multi-byte words are transferred most significant byte first.

The baud generator emits a tick every **176 clock cycles**, and the UART uses 16 ticks per bit. The calculated baud rate is 27,000,000 / (176 × 16) = approximately **9588.07 baud**, about -0.124% relative to 9600. The RTL comment says 175, but the counter includes both 0 and 175.

## PC to FPGA: coefficients

Send 200 signed 16-bit coefficient words, represented in two's complement:

```text
h[0] high byte, h[0] low byte,
h[1] high byte, h[1] low byte,
...
h[199] high byte, h[199] low byte
```

Total payload: **400 bytes**. There is no packet header, CRC, coefficient count field, or acknowledgment frame in this RTL. `led_done` is driven low after loading completes.

Examples: coefficient `0x1234` is sent as bytes `12 34`; coefficient -1 is sent as `FF FF`.

`coeff.hex` is a text file with one four-digit coefficient per line. A transfer utility must parse those lines and send their two binary bytes, rather than the ASCII characters.

## FPGA to PC: FIR results

Each output is a 41-bit raw accumulator word. The RTL forms a 48-bit transport buffer as:

```verilog
buffer <= {7'b0, d_in};
```

It then sends bytes `[47:40]`, `[39:32]`, `[31:24]`, `[23:16]`, `[15:8]`, and `[7:0]`.

This is **zero padding of the transport word**, not 48-bit sign extension. The Python decoder recovers the correct sign from bit 40:

```python
v41 = received_word & ((1 << 41) - 1)
signed_value = v41 - (1 << 41) if v41 >= (1 << 40) else v41
```

Examples:

| Raw FIR result | Six transmitted bytes | Decoded signed value |
|---|---|---:|
| 1231 | `00 00 00 00 04 CF` | 1231 |
| -1 | `01 FF FF FF FF FF` | -1 |

Keep groups aligned from the start of the run: the output has no sync marker. One deployment run produces 1000 results, or 6000 bytes. The Streamlit uploader expects a text HEX file containing one complete word per line; it does not parse arbitrary terminal logs or raw binary files.

## Fixed-point behavior

The app uses `scale = 2**15 - 1 = 32767`, rounds coefficients and input samples, and clips to [-32767, 32767]. The quantization therefore uses the app's exact 32767 scale, rather than assuming a 32768 scale.

The RTL multiplies signed samples by signed coefficients and accumulates 200 products in a signed 41-bit accumulator. It outputs the raw sum without final rounding, saturation, or a Q15 downshift. Python divides the decoded output by **2^30** for visualization and MSE calculation.

The included software reference uses integer convolution of the same quantized samples and coefficients, keeping the first 1000 outputs to match the ROM run. It does not stand in for a captured hardware output.

The app's `Fs = 8000 Hz` describes the designed test signal. It is not evidence of an 8 kHz live sample stream: input is ROM-driven, the FIR has handshakes, and output is buffered and sent through UART.
