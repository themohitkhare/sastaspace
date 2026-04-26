// Shared season constants. Previously hardcoded in 3 components — UI audit M4.
// Update these in one place to roll the season label across all surfaces.

export const SEASON_NUMBER = 1;
export const SEASON_DAY = 12;
export const SEASON_LENGTH = 30;

/** "season 1" — used in eyebrows, headers, footers. */
export const SEASON_LABEL = `season ${SEASON_NUMBER}`;

/** "season 1 · day 12 / 30" — used in topbars to show season progress. */
export const SEASON_PROGRESS_LABEL = `${SEASON_LABEL} · day ${SEASON_DAY} / ${SEASON_LENGTH}`;

/** "typewars · season 1 · a sasta lab project" — used in footer signatures. */
export const FOOTER_SIGNATURE = `typewars · ${SEASON_LABEL} · a sasta lab project`;
