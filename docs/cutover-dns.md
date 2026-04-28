# Cut-over DNS changes (manual)

After this branch merges to main and the first cargo-dist release is cut, update Cloudflare:

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

## Tunnel config (on prod box)
After DNS, edit the cloudflared tunnel config to remove the deleted hostnames; keep the route for `stdb.sastaspace.com`.
