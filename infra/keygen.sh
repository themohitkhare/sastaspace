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

openssl ecparam -name prime256v1 -genkey -noout -out keys/id_ecdsa
openssl ec -in keys/id_ecdsa -pubout -out keys/id_ecdsa.pub
chmod 600 keys/id_ecdsa
chmod 644 keys/id_ecdsa.pub

echo "wrote keys/id_ecdsa{,.pub}. back these up — losing them invalidates every existing identity."
