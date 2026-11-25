<?php

// Run during build and publication, before this image can receive a resolver job.
if (PHP_MAJOR_VERSION !== 8 || PHP_MINOR_VERSION !== 3) {
    throw new RuntimeException('The PHP 8.3 resolver requires PHP 8.3.');
}
foreach (['bcmath', 'curl', 'dom', 'gd', 'intl', 'mbstring', 'openssl', 'pcntl', 'pdo_mysql', 'pdo_sqlite', 'redis', 'xml', 'xmlwriter', 'zip'] as $extension) {
    if (!extension_loaded($extension)) {
        throw new RuntimeException('Missing required PHP extension: '.$extension);
    }
}
// The resolver must prove the same image encoder as the host: GD reads PNG and JPEG and writes WebP.
if (!function_exists('imagewebp') || empty(gd_info()['WebP Support']) || empty(gd_info()['JPEG Support']) || empty(gd_info()['PNG Support'])) {
    throw new RuntimeException('GD must read PNG and JPEG and write WebP.');
}
if (extension_loaded('rdkafka')) {
    throw new RuntimeException('The package resolver must prove operation without rdkafka.');
}
echo 'php83 platform: PHP '.PHP_VERSION.', required extensions and GD with WebP present, rdkafka absent'.PHP_EOL;
