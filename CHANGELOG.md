# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] — 2026-09-26

- Added a new **Wasabi Account Storage** service summing Active + Deleted storage across all buckets, for the account-wide total. Reuses the same agent section as the per-bucket check, so no changes to the Special Agent were needed.
- Switched size rendering from `render.disksize()` (decimal SI: 1 TB = 10^12 bytes) to `render.bytes()` (binary IEC: 1 TiB = 2^40 bytes). The underlying byte values were always correct; this only changes the displayed unit so they match what the Wasabi Console itself shows (which uses binary values but mislabels them "TB"/"GB" instead of "TiB"/"GiB").

## [1.0.0] — 2026-09-26 – Initial Release

- Automatic discovery of every bucket in a Wasabi account via the Stats API — no bucket names configured anywhere
- One service per bucket, reporting Active + Deleted storage utilization and their sum, with no thresholds
- Special Agent authenticates via `Authorization: <AccessKey>:<SecretKey>`, with the Secret Key stored in Checkmk's Password Store
- Stacked graph and perfometer (Active + Deleted = Total)
- Vanished buckets report UNKNOWN instead of crashing
