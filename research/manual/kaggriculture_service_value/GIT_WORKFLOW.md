# Manual Git workflow — publication is separate from the immediate screens

GitHub was **not accessed or updated** during preparation. The last supplied
baseline receipt identifies 7194116dfc92a8663139611233b5a221dad431a4; that is not a
claim that it is current remote main. The notebooks check local evidence/core
source before running. Do not fetch/reset just to make a check green.

Do this only after the two screens pass and their results have been reviewed.
The assistant does not execute any of these commands.

```bash
cd /home/sagemaker-user/projects/kaggriculture-manual
git status --short
git diff --stat
git branch --show-current
git log -1 --oneline
```

Preserve any unrelated changes. Review the source archive and its test receipts.
A source-only export helper is provided; it excludes outputs, credentials and raw
data and removes outputs from the *exported copies* of notebooks. Your executed
home-directory notebooks are preserved.

```bash
cd /home/sagemaker-user/projects/kaggriculture-manual
git switch -c research/service-value-rounds-19-20
python3 /home/sagemaker-user/kaggriculture_service_value/export_source.py
# Inspect the printed plan, then explicitly copy the source-only set:
python3 /home/sagemaker-user/kaggriculture_service_value/export_source.py --apply
git add -- research/manual/service_value
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

Review staged code and ensure no private outputs or raw episode files are staged.
Only then, using your own existing Git credentials:

```bash
git commit -m "Add service-value feature rounds with manual screen gates"
git push -u origin research/service-value-rounds-19-20
```

Open the repository in your browser, select **Compare & pull request**, review the
changes and required checks, and create the pull request. Merge only after checks
and human review. Do not commit a claim that the new tests passed without the
user-run receipt. Do not automatically upload executed notebooks/public data.

Source-only descendant commits are admitted when the recorded core hashes still match.
If core source or unrelated ancestry makes the preflight refuse, return
the status output for a compatibility review. Do not delete your package or
rewrite raw data. This stage does not require publishing before it can run.
