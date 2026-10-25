# RTL simulation

The report documents Xilinx ISE/ISim simulation with a 27 MHz clock, 200 coefficients, and a 10-sample test input. The supplied source text contains the deployment RTL with 1000-sample ROMs; the original testbench was not supplied.

The following report figures are included as historical evidence:

- [UART receiver](../docs/images/wave_uart_rx.png)
- [Coefficient loading](../docs/images/wave_coeff_first.png)
- [FIR computation](../docs/images/wave_fir_a.png)
- [FIFO](../docs/images/wave_fifo.png)
- [UART transmitter](../docs/images/wave_uart_tx.png)
- [Simulation summary](../docs/images/simulation_summary.png)

The report's integration stimulus is:

```text
x = {1231, -2345, -3457, -4569, 5671, -6783, 7995, -8907, 9019, -10131}
h = {1, 0, 0, ..., 0}  # 200 raw integer coefficients
```

In that test, y = x in raw accumulator units. `h[0] = 1` here is an integer identity-test coefficient, not the Q15 encoding of floating-point 1.0.

To recreate the original evidence, add the original testbench and its 10-sample memory configuration, run the documented tool, and archive the resulting raw logs. This package does not claim that the historical simulation was rerun or that a replacement testbench has been validated.
