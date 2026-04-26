pub const WORDS: &[&str] = &[
    "obliterate", "devastate", "onslaught", "annihilate",
    "cataclysm", "resistance", "liberation", "subjugate",
    "terminate", "overpower", "incinerate", "catastrophe",
    "abominable", "belligerent", "conflagration", "dreadnought",
    "extinguish", "fortified", "groundswell", "hemisphere",
    "incursion", "jurisdiction", "knighthood", "lancehead",
    "marauding", "nightwatch", "occupation", "pioneering",
    "quarantine", "relentless", "stratagem", "threshold",
    "unbounded", "vanquisher", "warlocked", "xenophobia",
    "zealousness", "abscission", "battlefront", "commandeer",
    "decimation", "embattled", "frontlines", "galvanize",
    "harbinger", "infiltrate", "juggernaut", "kingslayer",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_is_deterministic() {
        assert_eq!(select(7), select(7));
    }

    #[test]
    fn select_wraps_modulo_len() {
        assert_eq!(select(WORDS.len() as u64), WORDS[0]);
        assert_eq!(select(WORDS.len() as u64 * 3 + 5), WORDS[5]);
    }

    #[test]
    fn word_list_is_non_empty() {
        assert!(!WORDS.is_empty());
    }

    #[test]
    fn hard_words_are_at_least_eight_chars() {
        // Hard tier requires more keystrokes; floor at 8 chars.
        for w in WORDS {
            assert!(
                w.len() >= 8,
                "hard word `{w}` is shorter than the curation floor",
            );
        }
    }
}
