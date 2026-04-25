#!/usr/bin/env bash
# Generate the ECDSA P-256 JWT keypair SpacetimeDB uses to sign identities.
# Run ONCE on the prod box before first start. Keys persist in ./keys/.

set -euo pipefail

cd "$(dirname "$0")"
mkdir -p keys

if [[ -f keys/id_ecdsa && -f keys/id_ecdsa.pub ]]; then
  echo "keys already exist — refusing to overwrite. delete keys/ first if you really want to rotate."
  exit 1
fi

# SpacetimeDB uses the `jsonwebtoken` crate, which requires PKCS#8 PEM for ES256.
# `openssl genpkey` writes PKCS#8 by default; `openssl ecparam -genkey` writes
# SEC1, which jsonwebtoken rejects with `InvalidKeyFormat`.
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out keys/id_ecdsa
openssl ec -in keys/id_ecdsa -pubout -out keys/id_ecdsa.pub
# Lock the private key to owner-read only. The container reads it via a
# `:ro` bind mount, so it works as long as compose's `user:` matches the
# host uid that owns this directory (see docker-compose.yml).
chmod 700 keys
chmod 600 keys/id_ecdsa
chmod 644 keys/id_ecdsa.pub

echo "wrote keys/id_ecdsa{,.pub}. back these up — losing them invalidates every existing identity."
