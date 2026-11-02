# Portable workflow qualification

The root launcher was exercised using the public learning-image build and QEMU
positive/negative/recovery checks. The configured tool-container route passed
Simics Hello, physical Hello and real ADD–XOR–ADD PR with DDR restoration.
The PR input manifest used paths relative to its own directory under build/.
Historical all-example results remain separate; this is a fresh focused workflow
qualification, not a rerun of all 94 rows. Windows CI tests launcher/path routing,
not proprietary tools, a board, WSL USB forwarding or native Windows GDB.

The first optional MCP connection failed before programming because its Docker
stdin was closed; -i and a regression test corrected that transport preflight.
The failed attempt is retained under initial-mcp-preflight. Final Hello and PR
restoration passed. Saved text normalizes CRLF/NUL bytes; copied-evidence.json
retains both original and saved hashes. Build products/tools/FPGA images are not
bundled. Old absolute paths in these captures are provenance, not public setup
requirements. Executable defaults and guides use repository/build paths.
