pub const WORDS: &[&str] = &[
    "sovereignty",
    "transcendence",
    "illumination",
    "annihilation",
    "omnipotence",
    "resurgence",
    "cataclysmic",
    "invincible",
    "apocalypse",
    "supernova",
    "singularity",
    "constellation",
    "dominion",
    "radiance",
    "omniscience",
    "ascendancy",
    "revelation",
    "primordial",
    "celestial",
    "unstoppable",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_is_deterministic() {
        assert_eq!(select(13), select(13));
    }

    #[test]
    fn select_wraps_modulo_len() {
        assert_eq!(select(WORDS.len() as u64), WORDS[0]);
    }

    #[test]
    fn rare_word_list_is_non_empty() {
        assert!(!WORDS.is_empty());
    }

    #[test]
    fn rare_words_are_distinctly_long() {
        // The Codex injection should reward longer typing — rare words
        // must each be at least 8 chars (mostly 10+).
        for w in WORDS {
            assert!(
                w.len() >= 8,
                "rare word `{w}` is shorter than the curation floor",
            );
        }
    }
}
