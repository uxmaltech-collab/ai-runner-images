# Collab 0.2.3 recipe bindings

Recipes select the published Collab 0.2.3 runtime at CLI main
`63c60623eb3cd267f9ec06f252498b821740599a`. The release manifest and
base wheel are independently pinned in compatibility locks. The release
passed three isolated Linux profile installations and published byte readback.

The two QA recipes preserve existing canonical resource-catalog profiles.
Their source bytes match Repo main `3824bdccd2f331c6733157e882075d72eb544a61`;
the extraction record retains the earlier exact source commit and hashes.
No runner route is enabled by this source change. iOS operational validation
remains native/Tart; the Mobile QA Linux profile is a separate existing route.

Validation: 22 control-plane context checks with final published artifacts and
nine console relocation checks pass. See SUMMARY.json for retained initial
input failures and exact evidence. Image builds, host adoption and final
canaries are not claimed by these source and context checks.
