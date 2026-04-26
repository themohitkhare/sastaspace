pub const WORDS: &[&str] = &[
    "fire", "void", "war", "red", "ash", "run", "cut", "hit",
    "glow", "flux", "aim", "raw", "iron", "dust", "burn",
    "kill", "dark", "bolt", "claw", "wave", "edge", "core",
    "scar", "pulse", "node", "grip", "raze", "halt", "draw",
    "leap", "bind", "tear", "snap", "ward", "seal", "mark",
    "rush", "bane", "echo", "lock", "cast", "dusk", "dawn",
    "gate", "vex", "foe", "ruin", "arc", "step", "rock",
    "blaze", "clash", "crush", "drive", "earth", "faith", "forge",
    "ghost", "guard", "heart", "blitz", "lance", "march", "oath",
    "pact", "raise", "ridge", "rift", "siege", "skies", "slay",
    "smite", "storm", "surge", "swear", "sword", "titan", "torch",
    "trace", "trail", "tribe", "unity", "valor", "vault", "vigil",
    "vow", "wake", "wield", "wrath", "zone", "apex", "bear",
    "blade", "brave", "break", "crest", "cross", "cry", "deep",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_wraps_at_len_boundary() {
        assert_eq!(select(WORDS.len() as u64), WORDS[0]);
    }

    #[test]
    fn easy_word_list_is_non_empty() {
        assert!(!WORDS.is_empty());
    }
}
