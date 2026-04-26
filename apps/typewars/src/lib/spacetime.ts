import { DbConnection } from '@sastaspace/typewars-bindings';

export const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com';
export const STDB_MODULE =
  process.env.NEXT_PUBLIC_TYPEWARS_MODULE ?? 'typewars';

// JWT lives here regardless of which auth path issued it:
//   - legacy FastAPI flow: callback page writes after parsing the URL fragment
//   - STDB-native flow:    /auth/verify writes after verify_token + claim_progress_self
// Both flows store the same raw JWT minted by spacetime's POST /v1/identity,
// so spacetime.ts doesn't need to know which path produced it.
const TOKEN_KEY = 'typewars:auth_token';

function loadToken(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  return window.localStorage.getItem(TOKEN_KEY) ?? undefined;
}

function saveToken(token: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function buildConnection() {
  const builder = DbConnection.builder()
    .withUri(STDB_URI)
    .withDatabaseName(STDB_MODULE)
    .onConnect((_ctx, _identity, token) => {
      if (token) saveToken(token);
    });

  const existing = loadToken();
  return existing ? builder.withToken(existing) : builder;
}
