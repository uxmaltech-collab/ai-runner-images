# uxmaltech-base-image

This directory holds no recipe. The FrankenPHP runtime base of the uxmaltech
PHP flavors is owned by the source of truth: the component
`containers/uxmaltech-base-image` of `uxmaltech-collab/ai-templates-resources`
(Dockerfile, `build.sh`, `smoke.sh`, `version.json`, release rows). It is
released there and published as a recipe in `uxmaltech-collab/releases`; the
organization's console orders its build and keeps the image in the console's
registry.

The copy that lived here was an earlier state of that Dockerfile, not a
deliberate variant. It predated the source of truth's 0.1.1 and 0.1.2 fixes:
it installed `redis` and `opentelemetry` through `install-php-extensions` and
`rdkafka` through `pecl install rdkafka-<version>` by name, which fails when
pecl.php.net answers chunked, and it did not check that `opentelemetry` loads.
The source of truth installs the three PECL extensions from their release
tarballs. There is one recipe, and it is not here.
