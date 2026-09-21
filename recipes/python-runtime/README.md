# Relocatable Python consoles

`relocate_console.prepare_runtime` prepares a fresh copy when a generated CLI's
shebang or wheel RECORD still refers to its build location. The caller supplies
the exact console, distribution, entry point, Python version, final interpreter
root and its existing canonical path/tree hash functions. No customer package
identity is built into this recipe.

The recipe verifies the entry-point metadata and script import, preserves the
script body and modes, updates only a pre-existing console RECORD entry, and
checks that original inputs remain unchanged. Already-correct inputs are reused.
The receipt records changed bytes and source/prepared tree hashes. Nothing is
installed on the host or in a guest by this helper.

Run `python3 -m pytest -q recipes/python-runtime/test_relocate_console.py` to
exercise real execution of a relocated fixture plus malformed inputs and
preservation cases. Consumers pin the file by source commit and SHA-256 and
supply their own identity/bindings; they do not maintain a second implementation.
