# SwiftLint0.65.1 native component

`pins.json` locks the official portable zip, its binary and LICENSE independently. Keep large release bytes outside Git. `install.py` performs offline verification before installing in an owned virtual builder; it does not install Xcode, use Homebrew, download code or authenticate an agent.

```sh
python3 install.py --archive /absolute/portable_swiftlint.zip \
  --layout neutral --receipt /absolute/new-swiftlint-receipt.json
```

The neutral layout is `/opt/ai-runner-images/tools/swiftlint/0.65.1/{swiftlint,LICENSE}` and the regular launcher is `/opt/ai-runner-images/bin/swiftlint`. Declare that bin directory in the job PATH. Directories and executables are root-owned0755, LICENSE0644, independent of the operator's private umask. Existing destinations are preserved. The optional `consumer` layout reproduces the accepted tool and launcher paths under `/opt/macos-tart-bootstrap/resolver-tools` and `/opt/ai-repo-resources/python/bin`; consumer adoption remains its owner's task. This is a tool recipe, not a second CLI installer.

`--verify-inputs-only` checks the complete zip and exact two-member closure without native installation. The original strict codesign failure is retained: integrity here is the locked official bytes, not an invented signature claim.

Use `recipes/macos/qualify.py` for real lint under the canonical disposable nonadministrator session. `qualify.py` in this component also runs directly as that user, with `--output` pointing to a new directory under its actual HOME. It writes command results, JUnit and preserved failure logs for both a clean Swift file and a deliberate force-cast violation. A version check or numeric UID without a Directory Services account is insufficient.

The original accountless SwiftLint probes timed out in the toolchain lookup despite a passing version command. Those failures remain private immutable receipts; the later accepted iOS resolve demonstrated SwiftLint in its real job session. The neutral fixture separately demonstrates this shared recipe, without repeating that customer canary.
