# Commit, push and merge into the existing PUBLIC repository

Only follow this section after the README/notebook review and `READY_TO_COMMIT`.
No new GitHub repository is created. No visibility change is included. Do not
follow the superseded private-repository/portfolio migration instructions.

## 1. Browser login when needed

Use the existing Git credentials if already configured. For a browser/device flow
without pasting a token or password into the notebook:

```bash
cd /home/sagemaker-user/kaggriculture_public_release
export PATH="$HOME/.local/bin:$PATH"
python3 publication/install_gh.py
gh auth status --hostname github.com
```

The optional installer does nothing if `gh` is already on PATH. Otherwise it downloads
the official current stable Linux release and release checksum file, verifies SHA256,
and installs only `~/.local/bin/gh`. It does not modify the ML environment and uses
no sudo. It has a 90-second download limit. It has not been executed in preparation.

If `gh auth status` says you are not logged in:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Open the displayed GitHub device URL, enter the one-time code and complete the
browser authorization. Do not share tokens, auth files or terminal credential output.
If no credential store exists, gh may save credentials in its local configuration;
that directory is outside the allowlisted publication tree.

Verify the target without changing it:

```bash
gh repo view alvaromendizabal/kaggriculture \
  --json nameWithOwner,isPrivate,url
```

Require `nameWithOwner` to match and `isPrivate` to be `false`. If it is unexpectedly
private, stop and report that discrepancy; this workflow never toggles visibility.

## 2. Review the exact staged content

```bash
cd /home/sagemaker-user/projects/kaggriculture-publish
git remote get-url origin
git branch --show-current
git status --short
git diff --cached --check
git diff --cached --stat
git diff --cached -- README.md docs/research/evidence.md research/README.md
```

The branch must be `publication/manual-research-21-22` and origin must be the existing
`alvaromendizabal/kaggriculture`. Inspect the actual source/notebooks too, not only the
summary. The manifest controls staging; no broad `git add .` is required.

Commit identity must be your existing configured name/email. If Git reports no identity,
configure it locally in this checkout using your own verified or GitHub noreply email;
do not use an invented address. This is the only identity value not assumed by the guide.

## 3. Commit and push

```bash
git commit -m "Publish reproducible feature research, outcome notebooks, and evidence overview"
git push --set-upstream origin publication/manual-research-21-22
```

Do not force-push. A rejected push or divergence is a review point. A commit is only
local until the push succeeds. A pushed branch is not merged main.

## 4. Create and review the pull request

```bash
gh pr create --repo alvaromendizabal/kaggriculture \
  --base main --head publication/manual-research-21-22 \
  --title "Publish feature-research source, notebooks, and outcome evidence" \
  --body-file /home/sagemaker-user/kaggriculture_public_release/publication/PR_BODY.md
```

Open the returned PR URL. Read **Files changed** and **Checks**. Preserve all existing
required checks; the local publication checks did not execute the complete historical
research suite. No new workflow is added that silently launches AWS/Kaggle jobs.

```bash
gh pr checks publication/manual-research-21-22 --repo alvaromendizabal/kaggriculture
```

If checks are pending, inspect their progress on GitHub. If failing, stop and return
the failure; do not weaken or bypass them. If no checks exist, do not claim CI passed.
The local publication receipt still states precisely what it checked.

When the inspected PR is ready, click **Merge pull request** (or the enabled merge
method) and **Confirm merge** on GitHub. This is the user's explicit merge action.
No auto-merge, admin override, branch deletion, or history rewrite is prescribed.

## 5. Verify merge and synchronize the active AWS checkout

```bash
gh pr view publication/manual-research-21-22 \
  --repo alvaromendizabal/kaggriculture --json state,mergedAt,mergeCommit,url
```

Require `state` to be `MERGED` and a non-null merge receipt. Then:

```bash
cd /home/sagemaker-user/kaggriculture_public_release
python3 publication/publish.py sync
```

The helper verifies the actual remote main and approved file bytes before a clean,
non-destructive fast-forward of `projects/kaggriculture-manual`. Both merge and squash
PR strategies are supported because validation compares the resulting files and the
active baseline ancestry, not an assumed publication-branch ancestry.

## 6. Interactive public display (optional, after the reviewed merge)

Normal GitHub notebook rendering is static and does not execute custom JavaScript.
The repository includes the interactive HTML at `docs/research/index.html` for local
download. To serve it from the SAME public repository, explicitly open GitHub
Settings -> Pages -> Build and deployment -> Deploy from a branch -> main -> /docs.
Use the site URL shown by GitHub; no live Pages URL is claimed before deployment.
This optional owner action is separate from the commit/push/merge flow.

## Sources
- https://cli.github.com/manual/gh_auth_login
- https://cli.github.com/manual/gh_pr_create
- https://cli.github.com/manual/gh_pr_merge
- https://git-scm.com/docs/git-worktree
- https://git-scm.com/docs/git-bundle
- https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files
- https://docs.github.com/en/pages/quickstart
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
