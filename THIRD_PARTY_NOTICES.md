# Third-party notices

The BOSS browser connector was adapted from the user-provided `boss-agent-capability` package (MIT). Its conservative login, verification, duplicate-prevention and no-auto-retry design has been retained. The search route and workflow have been corrected and extended for this project.

Runtime and build dependencies keep their own licenses:

- `pypdf` — BSD-3-Clause; used for local PDF text extraction.
- `cryptography` — Apache-2.0 OR BSD-3-Clause; used to decrypt the public encrypted Moka job-list response for the Didi campus channel.
- `Playwright for Python` — Apache-2.0; optional source-only browser extra and not bundled in the base portable package.
- `PyInstaller` — GPL-2.0-or-later with the PyInstaller bootloader exception; used only to build the Windows portable package.

Refer to each dependency's installed distribution or upstream repository for the full license text and the exact transitive dependency set of a given build.
