// Centralised URLs so a single env override (E2E_BASE_*) re-targets every
// test at a non-prod stack.
export const LANDING = process.env.E2E_BASE_LANDING ?? "https://sastaspace.com";
export const NOTES = process.env.E2E_BASE_NOTES ?? "https://notes.sastaspace.com";
export const AUTH = process.env.E2E_BASE_AUTH ?? "https://auth.sastaspace.com";
export const ADMIN = process.env.E2E_BASE_ADMIN ?? "https://admin.sastaspace.com";
export const STDB_REST = process.env.E2E_BASE_STDB ?? "https://stdb.sastaspace.com";

export const STDB_DATABASE = process.env.E2E_STDB_DATABASE ?? "sastaspace";
