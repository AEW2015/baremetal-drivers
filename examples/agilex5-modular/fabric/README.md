# Fabric IP lab: ADD1 and XOR1

Read the [memory map, driver and deployment tutorial](https://aew2015.github.io/baremetal-drivers/fabric-ip/)
and [partial-reconfiguration integration lab](https://aew2015.github.io/baremetal-drivers/partial-reconfiguration/).

From the parent `examples/agilex5-modular` directory:

```sh
./fabric/test.sh                           # RTL + actual C driver, both personas
./fabric/check_component.sh                # Quartus component wrapper generation
LAB_CPU_BASE=0x20020000 ./fabric/build.sh    # proposed map; verify your design
python3 fabric/run.py --persona add         # metadata check only
```

The sources are executable teaching components, not a fitted whole-board Modular
project. Integration needs your matching HPS/DDR design and address map. The host
`fabric/run.py --run` entry uses matched full images and restores DDR Hello;
it does not perform partial reconfiguration. The PR directory contains an
assignment example, not a bitstream uploader or complete PR static shell.

ADD/XOR co-simulation and software builds have passed. New physical fabric
integration and live PR have not been qualified. See `../validation/fabric-ip/`
for the check manifest and captured evidence.
