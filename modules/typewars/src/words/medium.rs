pub const WORDS: &[&str] = &[
    "oblique", "cipher", "fractal", "embark", "fervent",
    "ignite", "herald", "invoke", "latent", "mortal",
    "nebula", "oblige", "pariah", "quartz", "resist",
    "solace", "thresh", "unfurl", "vertex", "warden",
    "zenith", "ablaze", "brazen", "combat", "dagger",
    "emblem", "falcon", "gambit", "hunter", "impact",
    "jagged", "kindle", "legion", "menace", "nether",
    "onrush", "pallor", "rankle", "scorch", "torment",
    "unbind", "vortex", "wither", "expose", "zealot",
    "abrupt", "beacon", "candor", "defiant", "eclipse",
    "flicker", "granite", "hostile", "igneous", "justice",
    "kinesis", "liberate", "monarch", "nuclear", "obscure",
    "phantom", "quantum", "rapture", "sanctum", "tempest",
    "unknown", "vagrant", "warfare", "xenolith", "yeoman",
    "abandon", "barrage", "crusade", "destiny", "eternal",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_is_deterministic() {
        assert_eq!(select(0), select(0));
        assert_eq!(select(42), select(42));
    }

    #[test]
    fn select_wraps_modulo_len() {
        // nonce equal to len returns the first word.
        assert_eq!(select(WORDS.len() as u64), WORDS[0]);
        // nonce one less than len returns the last word.
        assert_eq!(select(WORDS.len() as u64 - 1), WORDS[WORDS.len() - 1]);
    }

    #[test]
    fn word_list_is_non_empty() {
        assert!(!WORDS.is_empty());
    }

    #[test]
    fn medium_words_are_at_least_six_chars() {
        // The deck is curated to medium-difficulty words; sanity check
        // that nothing trivially-easy snuck in.
        for w in WORDS {
            assert!(
                w.len() >= 6,
                "medium word `{w}` is shorter than the curation floor",
            );
        }
    }
}
