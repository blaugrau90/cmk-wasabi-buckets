# Wasabi Bucket Utilization – Checkmk 2.5 Plugin

A Checkmk 2.5 MKP plugin that monitors the storage utilization of every bucket in a **Wasabi** cloud storage account via the Wasabi Stats API. Buckets are discovered automatically — no bucket names are configured anywhere.

**Requires:** Checkmk 2.5.0+ (CRE/CEE/CME) · Wasabi API key with Stats API access · GPLv3 License

---

## Features

- **Automatic bucket discovery** via the Wasabi Stats API — no bucket names configured anywhere; new buckets appear after the next service discovery, deleted ones drop out
- One service per bucket: **Wasabi Bucket \<name\>**, showing **Active** and **Deleted** storage (the two components Wasabi actually bills for) plus their sum
- A single **Wasabi Account Storage** service summing Active + Deleted storage across **all** buckets — the account-wide total
- **No thresholds** — services are always OK; they exist purely to expose values and metrics for graphing
- Stacked graph and perfometer: Active + Deleted, summing visually to total utilization (per bucket and account-wide)
- A bucket that disappears from the API (e.g. deleted) reports **UNKNOWN** instead of crashing, until the next discovery run drops the service entirely
- Secret Key is passed through Checkmk's **Password Store** — never stored in plaintext in the rule

---

## Wasabi Permissions

The Access Key used by this plugin only needs read access to billing/utilization data, not to the buckets themselves. In the Wasabi Console, create (or use) a user and attach the built-in **`WasabiAccountStatsAccess`** policy to it — this grants exactly the read-only access needed for the Stats API endpoint used here, without granting any S3 data access. A full Root Account key also works, but a dedicated user with just this policy is the safer, least-privilege option for monitoring.

---

## Installation

### Via Checkmk GUI (recommended)

1. Download `wasabi-1.1.0.mkp` from the [Releases](https://github.com/blaugrau90/cmk-wasabi-buckets/releases) page
2. In Checkmk: **Setup → Extension Packages → Upload package**
3. Upload the `.mkp` file and click **Install**

### Via CLI (as site user)

```bash
mkp add wasabi-1.1.0.mkp
mkp enable wasabi
```

### Create the dummy host

The Wasabi account is represented by a single host that has no real network address — Checkmk fetches all data through the special agent.

1. **Setup → Hosts → Add host**, e.g. name it `wasabi-account`
2. Set **Checkmk agent / API integrations** to **Configured API integrations, no Checkmk agent**
3. Set **IP address family** to **No IP**

### Assign the Special Agent rule

Under **Setup → Agents → Other integrations → Wasabi Storage Utilization**, create a rule and assign it to the dummy host:

| Field | Value |
|---|---|
| Wasabi Access Key | Your Wasabi Access Key ID |
| Wasabi Secret Key | The matching Secret Key — enter directly or, recommended, pick from the Password Store |
| Stats API base URL | Default `https://stats.wasabisys.com`, only change for special setups |
| Lookback period | Default 30 days. Wasabi's daily utilization snapshots can lag by several days before they appear in the Stats API — a short window (e.g. 2 days) can return no data at all |

Access Key and Secret Key are combined by the special agent into `Authorization: <AccessKey>:<SecretKey>`, as required by the Wasabi Stats API.

### Run the first discovery

Run **Service discovery** on the dummy host. One service `Wasabi Bucket <name>` appears per bucket returned by the Wasabi account, plus a single `Wasabi Account Storage` service for the account-wide total.

### Enable Periodic Service Discovery (recommended)

So that newly created Wasabi buckets show up automatically without manual intervention (and deleted buckets get marked vanished), add a rule under **Setup → Hosts → Periodic service discovery** for the dummy host, e.g. once a day.

---

## Configuration

There is no check-parameters ruleset — the check has no thresholds by design. The only configurable values are the Special Agent settings above (Access Key, Secret Key, base URL, lookback period).

### Service states

| Service | State | Condition |
|---|---|---|
| Wasabi Bucket \<name\> | OK | Bucket present in the API response (always, regardless of size) |
| Wasabi Bucket \<name\> | UNKNOWN | A previously discovered bucket no longer appears in the API response (e.g. deleted) |
| Wasabi Account Storage | OK | At least one bucket is present in the API response |
| Wasabi Account Storage | UNKNOWN | No bucket data available at all (e.g. the special agent returned nothing) |

---

## How It Works

```
Checkmk Check Cycle
  └─ Special agent (agent_wasabi, runs on the Checkmk site)
       ├─ GET /v1/standalone/utilizations/bucket (paginated, pageSize=100)
       ├─ Reduces multiple daily records per bucket to the newest by EndTime
       └─ Emits one JSON line per bucket
  └─ Checkmk Section  <<<wasabi_bucket_utilization:sep(0)>>>
       {"bucket": "my-bucket", "region": "eu-central-1",
        "active_bytes": 123456789, "deleted_bytes": 4567, ...}
  └─ Check plugins (wasabi/agent_based/), both sharing the section above
       ├─ wasabi_bucket_utilization:  one service per bucket
       └─ wasabi_account_utilization: one service, summed across all buckets
       Both report Active + Deleted + Total as metrics, always OK
```

---

## File Structure

```
wasabi/
├── rulesets/wasabi.py                       # Setup rule: Access Key, Secret Key, base URL, lookback
├── server_side_calls/special_agent.py       # Builds the agent_wasabi call, handles the Secret
├── agent_based/wasabi_bucket_utilization.py # Parse / discovery / check logic
├── graphing/wasabi_bucket_utilization.py    # Metrics, stacked graph, perfometer
└── libexec/agent_wasabi                     # Special agent script (queries the Wasabi Stats API)
packages/wasabi                              # MKP manifest
tests/                                       # pytest unit tests
```

---

## Building from Source

Run as root on the Checkmk server:

```bash
# Deploy files to the site (replace <site> with your site name)
SITE=<site>

install -m 755 -D wasabi/libexec/agent_wasabi \
    /omd/sites/$SITE/local/share/check_mk/agents/special/agent_wasabi

ADDONS=/omd/sites/$SITE/local/lib/python3/cmk_addons/plugins/wasabi
install -m 644 -D wasabi/agent_based/wasabi_bucket_utilization.py "$ADDONS/agent_based/wasabi_bucket_utilization.py"
install -m 644 -D wasabi/rulesets/wasabi.py "$ADDONS/rulesets/wasabi.py"
install -m 644 -D wasabi/server_side_calls/special_agent.py "$ADDONS/server_side_calls/special_agent.py"
install -m 644 -D wasabi/graphing/wasabi_bucket_utilization.py "$ADDONS/graphing/wasabi_bucket_utilization.py"

chown -R $SITE:$SITE /omd/sites/$SITE/local/share/check_mk/agents/special/agent_wasabi "$ADDONS"

# Build MKP (as site user)
cp packages/wasabi /omd/sites/$SITE/var/check_mk/packages/wasabi
su - $SITE -c "mkp package /omd/sites/$SITE/var/check_mk/packages/wasabi"
```

The resulting `.mkp` file will be in `/omd/sites/$SITE/var/check_mk/packages_local/`.

### Testing locally, without a Checkmk site

```bash
python3 wasabi/libexec/agent_wasabi --access-key <ACCESS-KEY> --secret-key <SECRET-KEY>
```

Expected output:

```
<<<wasabi_bucket_utilization:sep(0)>>>
{"bucket": "my-bucket", "region": "eu-central-1", "active_bytes": 123456789, "deleted_bytes": 4567, "padded_bytes": 123461356, "end_time": "2026-09-25T00:00:00Z"}
```

On the Checkmk site (after installation):

```bash
cmk -d wasabi-account      # shows the raw agent section
cmk -vI wasabi-account     # runs service discovery
cmk -v wasabi-account      # runs the actual check
```

### Unit tests

```bash
pip install pytest
pytest tests/
```

`cmk.agent_based.v2` only exists inside a Checkmk site's Python environment. `tests/conftest.py` registers a minimal stand-in for it — reproducing only the runtime surface the plugin actually uses — when the real module isn't importable, so the check-plugin tests also run standalone.

---

## Wasabi Stats API

- `GET /v1/standalone/utilizations/bucket` (paginated via `pageSize`/`pageNum`, capped at `pageSize=100` by the API; time window via `from`/`to`) returns utilization records for **all** buckets in one call — this is what makes automatic discovery possible. The response is wrapped as `{"PageInfo": {...}, "Records": [...]}`. If a bucket has multiple records in the window, the special agent picks the one with the newest `EndTime`.
- The per-bucket endpoints (`/bucket/:bucketName`, `/bucket/:bucketNumber`) are intentionally not used — they play no role in automatic discovery, and the bucket-number variant additionally requires an undocumented `X-Wasabi-Service` header.

## Error Handling

If the API call fails (connection error, timeout, HTTP error, invalid JSON response), `agent_wasabi` prints a clear message to stderr and exits with code `1` — Checkmk then marks the data source as failed instead of silently processing incomplete data.

---

## License

GPLv3 — see [LICENSE](LICENSE)

## Author

Luca-Leon Hausdoerfer — [github.com/blaugrau90](https://github.com/blaugrau90)
