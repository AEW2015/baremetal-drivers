# Build and update this website

The source is Markdown in `docs/`, with navigation in `mkdocs.yml`. It uses
MkDocs Material and GitHub Pages; the example sources remain in the same repo.

From the repository root on a Python 3 development machine:

```sh
python3 -m venv .venv-docs
. .venv-docs/bin/activate
python3 -m pip install -r docs/requirements.txt
mkdocs build --strict
mkdocs serve --dev-addr 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/baremetal-drivers/` (or the URL printed by MkDocs) to
preview. Generated `site/` and the virtual environment are untracked.

The GitHub Actions workflow builds the site, runs the freestanding QEMU smoke
check, student-failure regressions (including an intentional QEMU failure) and deploys the static output after a push to `main`. Pull requests build
and check without publishing. No FPGA image is programmed by CI, and GitHub's
runner has no access to the bench.

The QEMU CI job uses Ubuntu's AArch64 Linux cross compiler with `-nostdlib` for
this freestanding exercise. The developer tutorial and hardware builds use the
pinned `aarch64-none-elf-` toolchain. Both emit an AArch64 ELF without a Linux
runtime; CI does not qualify the board examples or the pinned compiler build.

See [MkDocs deployment guidance](https://www.mkdocs.org/user-guide/deploying-your-docs/)
and [GitHub's Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
