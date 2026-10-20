<?php

// Run during build and publication, before this image can receive a resolver job.
if (PHP_MAJOR_VERSION !== 8 || PHP_MINOR_VERSION !== 3) {
    throw new RuntimeException('The storefront-core-pkg resolver requires PHP 8.3.');
}
foreach (['bcmath', 'curl', 'dom', 'gd', 'intl', 'mbstring', 'openssl', 'pcntl', 'pdo_sqlite', 'redis', 'xml', 'xmlwriter', 'zip'] as $extension) {
    if (!extension_loaded($extension)) {
        throw new RuntimeException('Missing required PHP extension: '.$extension);
    }
}
// CMS image uploads are recompressed to WebP on the host; the resolver must prove the same encoder.
if (!function_exists('imagewebp') || empty(gd_info()['WebP Support']) || empty(gd_info()['JPEG Support']) || empty(gd_info()['PNG Support'])) {
    throw new RuntimeException('GD must read PNG and JPEG and write WebP.');
}
if (extension_loaded('rdkafka')) {
    throw new RuntimeException('The package resolver must prove operation without rdkafka.');
}
echo 'storefront-core-pkg platform: PHP '.PHP_VERSION.', required extensions and GD with WebP present, rdkafka absent'.PHP_EOL;
