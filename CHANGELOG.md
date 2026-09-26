# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-09-26 – Initial Release

- Automatic discovery of every bucket in a Wasabi account via the Stats API — no bucket names configured anywhere
- One service per bucket, reporting Active + Deleted storage utilization and their sum, with no thresholds
- Special Agent authenticates via `Authorization: <AccessKey>:<SecretKey>`, with the Secret Key stored in Checkmk's Password Store
- Stacked graph and perfometer (Active + Deleted = Total)
- Vanished buckets report UNKNOWN instead of crashing
