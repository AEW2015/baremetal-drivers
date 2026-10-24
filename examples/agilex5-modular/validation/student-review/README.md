# Simulated student review evidence

See the [public review](https://aew2015.github.io/baremetal-drivers/student-review/)
for methods, feedback and limitations. Personas are agent simulations, not real
students. Logs here are actual technical executions, with local paths and line
endings normalized; nonprintable UART bytes are escaped. Hardware results cover the revised core runner and DDR Hello
restoration; they do not rerun the historical 15-example campaign. No desktop
VS Code session, physical power-loss or USB-disconnect injection was exercised.

`manifest.json` records software hashes and the selected hardware run. The ELF
and FPGA images are local generated artifacts; hashes identify what was tested.
The host UART in normalized logs means the verified SOM J2 connection.
