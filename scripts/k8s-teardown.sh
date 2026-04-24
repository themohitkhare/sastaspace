#!/usr/bin/env bash
# scripts/k8s-teardown.sh
#
# Safely scales Next.js deployments to 0 and deletes their Services and
# Ingresses. Leaves Postgres, cloudflared, and LiteLLM untouched.
#
# Usage:
#   ./scripts/k8s-teardown.sh             # dry-run (prints what would be done)
#   ./scripts/k8s-teardown.sh --execute   # actually delete
#
# The dry-run flag is the default. You must pass --execute explicitly to make
# any changes.
#
# What is torn down:
#   Deployments:  landing, almirah, gotrue, postgrest, studio, pg-meta, gateway
#   Services:     landing, almirah, gotrue, postgrest, studio, pg-meta, gateway
#   Ingresses:    landing-ingress, api-ingress, almirah
#
# What is preserved (never touched):
#   Deployment:   postgres            (the database — still used by Rails)
#   Service:      postgres
#   Deployment:   litellm             (cluster-local AI backend)
#   Service:      litellm
#   Namespace:    sastaspace          (left in place)
#   ConfigMaps:   any                 (left in place)
#   Secrets:      any                 (left in place — contain DB creds)
#   PersistentVolumeClaims: any       (left in place — contain Postgres data)
#   DaemonSet:    nginx-ingress-microk8s-controller  (left in place — stopped
#                 separately in the cutover runbook; Kamal does not own it)

set -euo pipefail

NAMESPACE="sastaspace"
DRY_RUN=true

# Parse flags
for arg in "$@"; do
  case "$arg" in
    --execute) DRY_RUN=false ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help)
      echo "Usage: $0 [--execute|--dry-run]"
      echo "  Default is dry-run. Pass --execute to apply changes."
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg" >&2
      exit 1
      ;;
  esac
done

# ---- Resources to remove ----

# Deployments: Next.js apps + Supabase ancillaries (NOT postgres, NOT litellm)
DEPLOYMENTS=(
  landing
  almirah
  gotrue
  postgrest
  studio
  pg-meta
  gateway
)

# Services matching deployments above
SERVICES=(
  landing
  almirah
  gotrue
  postgrest
  studio
  pg-meta
  gateway
)

# Ingress objects
INGRESSES=(
  landing-ingress
  api-ingress
  almirah
)

# ---- Helpers ----

KUBECTL="sudo microk8s kubectl -n $NAMESPACE"

resource_exists() {
  local kind="$1"
  local name="$2"
  $KUBECTL get "$kind" "$name" &>/dev/null
}

print_header() {
  echo ""
  echo "============================================================"
  echo " k8s-teardown.sh — $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "EXECUTE MODE")"
  echo " Namespace: $NAMESPACE"
  echo "============================================================"
}

print_preserved() {
  echo ""
  echo "Preserved (will NOT be touched):"
  echo "  Deployment/Service: postgres"
  echo "  Deployment/Service: litellm"
  echo "  Namespace:          $NAMESPACE"
  echo "  All Secrets, ConfigMaps, PVCs"
  echo "  nginx-ingress controller DaemonSet"
  echo ""
}

# ---- Main ----

print_header
print_preserved

echo "--- Deployments to scale-to-0 then delete ---"
for d in "${DEPLOYMENTS[@]}"; do
  if resource_exists deployment "$d"; then
    REPLICAS=$($KUBECTL get deployment "$d" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "?")
    echo "  deployment/$d  (current replicas: $REPLICAS)"
    if [ "$DRY_RUN" = false ]; then
      echo "    → scaling to 0..."
      $KUBECTL scale deployment "$d" --replicas=0
      echo "    → deleting deployment/$d..."
      $KUBECTL delete deployment "$d" --grace-period=30
    fi
  else
    echo "  deployment/$d  [not found — skip]"
  fi
done

echo ""
echo "--- Services to delete ---"
for s in "${SERVICES[@]}"; do
  if resource_exists service "$s"; then
    echo "  service/$s"
    if [ "$DRY_RUN" = false ]; then
      echo "    → deleting service/$s..."
      $KUBECTL delete service "$s"
    fi
  else
    echo "  service/$s  [not found — skip]"
  fi
done

echo ""
echo "--- Ingresses to delete ---"
for i in "${INGRESSES[@]}"; do
  if resource_exists ingress "$i"; then
    echo "  ingress/$i"
    if [ "$DRY_RUN" = false ]; then
      echo "    → deleting ingress/$i..."
      $KUBECTL delete ingress "$i"
    fi
  else
    echo "  ingress/$i  [not found — skip]"
  fi
done

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN complete. No changes made."
  echo "Run with --execute to apply the above deletions."
else
  echo "EXECUTE complete. Verifying remaining resources..."
  echo ""
  echo "--- Remaining Deployments ---"
  $KUBECTL get deployments
  echo ""
  echo "--- Remaining Services ---"
  $KUBECTL get services
  echo ""
  echo "--- Remaining Ingresses ---"
  $KUBECTL get ingresses 2>/dev/null || echo "(none)"
  echo ""
  echo "Teardown done. Postgres and LiteLLM are still running."
fi
