import { DbConnection } from '@sastaspace/typewars-bindings';

export const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com';
export const STDB_MODULE =
  process.env.NEXT_PUBLIC_TYPEWARS_MODULE ?? 'typewars';

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
