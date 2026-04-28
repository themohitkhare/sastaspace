# Cut-over manual steps

The TUI migration is code-complete and v0.1.1 is published. Three remaining items require explicit human access I deliberately didn't reach for from automation:

## 1. Cloudflare DNS

Update Cloudflare:

## Delete
- `landing.sastaspace.com` (CNAME → tunnel)
- `notes.sastaspace.com` (CNAME → tunnel)
- `typewars.sastaspace.com` (CNAME → tunnel)
- `admin.sastaspace.com` (CNAME → tunnel)
- `deck.sastaspace.com` (CNAME → tunnel)
- `auth.sastaspace.com` (CNAME → tunnel)

## Keep / repoint
- `stdb.sastaspace.com` — unchanged (still pointing at the prod box's tunnel)
- `sastaspace.com` (apex) — repoint to GitHub Pages serving the README + install.sh. Set the GitHub Pages source to the `gh-pages` branch (or the main branch root). Ensure `install.sh` and `README.md` end up at the served root.

## 2. Tunnel config + container shutdown (on prod box `taxila`, 192.168.0.37)
After DNS, ssh in and:
- Edit the cloudflared tunnel config to remove the deleted hostnames; keep the route for `stdb.sastaspace.com`. Restart `cloudflared`.
- Stop and remove the now-unused containers:
  ```bash
  docker compose stop landing notes admin typewars auth deck
  docker compose rm -f  landing notes admin typewars auth deck
  ```

## 3. Homebrew tap PAT (for future auto-releases)
v0.1.1's tap formula was published manually. cargo-dist's `publish-homebrew-formula` job needs a cross-repo Personal Access Token to push to `themohitkhare/homebrew-sastaspace` automatically:

1. Create a PAT at https://github.com/settings/personal-access-tokens/new
   - Resource owner: `themohitkhare`
   - Repository access: only `themohitkhare/homebrew-sastaspace`
   - Repository permissions → Contents: `Read and write`
2. Add it as a repo secret in `themohitkhare/sastaspace`:
   ```bash
   gh secret set HOMEBREW_TAP_TOKEN --repo themohitkhare/sastaspace --body "<paste-pat>"
   ```
3. cargo-dist 0.31's release workflow expects this token name out of the box. (If a different name surfaces in CI logs, update accordingly.)

After this, the next `git tag -a vX.Y.Z && git push origin vX.Y.Z` triggers a fully-automated release including the tap update.

## Verify the binary

Before flipping DNS, kick the tires locally:
```bash
brew install themohitkhare/sastaspace/sastaspace
sastaspace                       # opens portfolio splash; q to quit
```
Or via the install script:
```bash
curl -sSf https://github.com/themohitkhare/sastaspace/releases/latest/download/shell-installer.sh | sh
```
