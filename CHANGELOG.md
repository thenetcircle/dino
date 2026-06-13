# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.23.16] - 2026-06-13

### Fixed

- **WIO presence**: Prevent `user:status` from staying at `1` (available) after disconnect when the user has already been removed from `users:online:set`. The offline pipeline now reads pre-offline status from the DB before updating Redis, so a later `get_user_status(skip_cache=True)` backfill cannot overwrite the offline status.
