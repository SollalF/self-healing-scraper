# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1](https://github.com/SollalF/self-healing-scraper/compare/self-healing-scraper-v0.3.0...self-healing-scraper-v0.3.1) (2026-08-11)


### Bug Fixes

* share content-aware HTML sampling between create and repair ([#4](https://github.com/SollalF/self-healing-scraper/issues/4)) ([ea3a2a5](https://github.com/SollalF/self-healing-scraper/commit/ea3a2a50a9f5ea402b0a6f926f171bd029d1027f))

## [0.3.0](https://github.com/SollalF/self-healing-scraper/compare/self-healing-scraper-v0.2.0...self-healing-scraper-v0.3.0) (2026-08-09)


### ⚠ BREAKING CHANGES

* ParserStore implementations must add a find_cached_run method returning CachedRun | None.
* remove legacy validation check migration
* make Settings a plain parameter object

### Features

* add date_parseable checks and migrate legacy news validators ([6ab138f](https://github.com/SollalF/self-healing-scraper/commit/6ab138fcb4d8af0d5e816572801e38d82dba05e0))
* require JSON Schema structured LLM outputs ([e1d2802](https://github.com/SollalF/self-healing-scraper/commit/e1d28024a2f32057c77595d40544322e2b4507ed))
* reuse stored runs for already-scraped pages ([73732cc](https://github.com/SollalF/self-healing-scraper/commit/73732cc217710bc1cdc56acd48157bd148706501))


### Code Refactoring

* make Settings a plain parameter object ([e7dffd0](https://github.com/SollalF/self-healing-scraper/commit/e7dffd0b9caa24de22c3dacfa14e6b17db7cf285))
* remove legacy validation check migration ([2e7d241](https://github.com/SollalF/self-healing-scraper/commit/2e7d2410b4abc68e2caeed0ddafa97c21f0f4827))

## [0.2.0](https://github.com/SollalF/self-healing-scraper/compare/self-healing-scraper-v0.1.0...self-healing-scraper-v0.2.0) (2026-08-04)


### ⚠ BREAKING CHANGES

* remove legacy validation check migration
* make Settings a plain parameter object

### Features

* add date_parseable checks and migrate legacy news validators ([6ab138f](https://github.com/SollalF/self-healing-scraper/commit/6ab138fcb4d8af0d5e816572801e38d82dba05e0))
* require JSON Schema structured LLM outputs ([e1d2802](https://github.com/SollalF/self-healing-scraper/commit/e1d28024a2f32057c77595d40544322e2b4507ed))


### Code Refactoring

* make Settings a plain parameter object ([e7dffd0](https://github.com/SollalF/self-healing-scraper/commit/e7dffd0b9caa24de22c3dacfa14e6b17db7cf285))
* remove legacy validation check migration ([2e7d241](https://github.com/SollalF/self-healing-scraper/commit/2e7d2410b4abc68e2caeed0ddafa97c21f0f4827))

## [0.1.0](https://github.com/SollalF/self-healing-scraper/releases/tag/v0.1.0) (2026-07-26)

### Features

* Initial self-healing scrape engine with `ParserStore` Protocol and `ScrapeDomain` plug-in
