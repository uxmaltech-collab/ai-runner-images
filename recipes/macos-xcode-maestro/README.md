# Native tools base

Create a stopped-parent APFS copy using `scripts/tart-layer.py`; the original tuple must remain untouched. This artifact recipe starts from the retained, accountless Xcode/Maestro builder. It is not an executor installation or image admission.

Run `neutralize.py` through root RPC **inside that new builder only**, with `AI_IMAGE_LAYER=macos-xcode-maestro`. Stage the dated record of the retained builder's neutralization, `provenance/native-base-20260916.json`, with it and pass that copy as `--record`: the record lists the inventoried legacy consumer/agent paths and their exact inventories. The recipe verifies retained executables, requires every recorded path to be present and to match its inventory, and only then removes those paths and nothing else. The receipt records the scope and exact surviving executable hashes. No ordinary account or runtime session may exist.

Stream the existing canonical RPC binary into `install-rpc.py` through the same RPC. Expected SHA-256: `a1c66855a250108ea05fc4f672f1099dfd1c315a012dee343c282aab83933952` (12,835,808 bytes). This preserves the existing root launch daemon and takes effect on the next boot. The original canary's canonical build and source receipts remain the provenance authority; this repository does not fork that component.

Verify the tool paths and versions, shut down the owned builder normally, then hash the stopped config/NVRAM/disk tuple while holding its configuration lock. Record both the actual clone receipt and parent manifest. The resulting tools base is local artifact storage until separately published/admitted.

The next layer installs **Codex, Claude and Grok-build together**. The third adds Flutter and Dart. Qualification accounts are created only in a disposable child of the sealed final layer.
