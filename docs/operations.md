# Operations Runbook

## One-time dedupe backfill after deploy

After deploying the connected-components dedupe update, run a full dedupe pass once so historical articles are reclustered and stories gain missing sources.

1. Confirm `DEDUP_THRESHOLD` for the target environment (default is `0.70`).
2. Run a one-time dedupe backfill:

```bash
fr-embed --with-dedup
```

Fallback if the entrypoint script is unavailable:

```bash
python -m fundus_recommend.cli.embed --with-dedup
```

3. Verify scheduler/application logs report dedupe metrics:
`threshold`, `reassigned`, `clustered_articles`, `clusters`, and `max_cluster_size`.
