# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] — 2026-11-09

- **Fixed buckets still going missing / reported as "no longer reported by the Wasabi API" (actual root cause).** The Wasabi Stats API paginates **zero-based** (`pageNum=0` is the first page and the default). The agent started at `pageNum=1` and therefore skipped the first 100 records. The API returns about 31 days of daily records, sorted by time, so what remained was only the tail of that list. Which buckets appeared in that tail depended on where the 100-record page boundary happened to fall, so a bucket could vanish for days and reappear whenever a new daily record shifted the boundary. The agent now starts at `pageNum=0` and reads all pages.
- This also explains why requests with a `from`/`to` window seemed to "drop" buckets or return nothing: a short window holds fewer than 100 records, so the (skipped) first page held all of them and the second page was empty. The explanation given for 1.2.0 (time window silently drops buckets) was therefore incomplete; removing the window was harmless but not the real fix. The *Lookback period* setting stays removed.
- Added a safety stop if pagination never ends, and regression tests for the zero-based paging.
- **Deleted buckets are shown as obsolete for a limited time.** The API keeps returning a deleted bucket's last records for ~31 days. A bucket whose newest record is 2 or more days behind the newest record of the account is now reported as **obsolete** (service goes WARN: "no utilization data since <date>, bucket was probably deleted") and no new service is discovered for it. Once it is more than 7 days behind, the agent stops reporting it, so the service disappears. Obsolete buckets are excluded from the **Wasabi Account Storage** total. The age is measured against the API's own newest record, not the local clock, so a delay on Wasabi's side does not mark anything obsolete.

## [1.2.0] — 2026-11-05

- **Fixed buckets randomly missing / reported as "no longer reported by the Wasabi API".** The Wasabi Stats API silently drops buckets from its response when a `from`/`to` time window is sent (reproduced with a 30-day window, without `latest`, and with `to` set to tomorrow; the same request without a window returned all buckets). The special agent sent `from`, `to` and `latest=true` on every request, so affected buckets intermittently (typically around Wasabi's nightly recalculation) or permanently vanished and their services went UNKNOWN. The agent now sends no time filter and picks the newest record per bucket itself.
- The **Wasabi Account Storage** total no longer undercounts: buckets that were dropped by the API were previously missing from the sum.
- **Removed the *Lookback period* setting** (and the agent's `--lookback-days` option), since the time window it controlled is what made the API drop buckets. Existing rules are migrated automatically; the value is simply discarded.

## [1.1.0] — 2026-09-26

- Added a new **Wasabi Account Storage** service summing Active + Deleted storage across all buckets, for the account-wide total. Reuses the same agent section as the per-bucket check, so no changes to the Special Agent were needed.
- Switched size rendering from `render.disksize()` (decimal SI: 1 TB = 10^12 bytes) to `render.bytes()` (binary IEC: 1 TiB = 2^40 bytes). The underlying byte values were always correct; this only changes the displayed unit so they match what the Wasabi Console itself shows (which uses binary values but mislabels them "TB"/"GB" instead of "TiB"/"GiB").

## [1.0.0] — 2026-09-26 – Initial Release

- Automatic discovery of every bucket in a Wasabi account via the Stats API — no bucket names configured anywhere
- One service per bucket, reporting Active + Deleted storage utilization and their sum, with no thresholds
- Special Agent authenticates via `Authorization: <AccessKey>:<SecretKey>`, with the Secret Key stored in Checkmk's Password Store
- Stacked graph and perfometer (Active + Deleted = Total)
- Vanished buckets report UNKNOWN instead of crashing
