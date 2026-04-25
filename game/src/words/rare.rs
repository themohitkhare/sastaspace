pub const WORDS: &[&str] = &[
    "sovereignty", "transcendence", "illumination", "annihilation",
    "omnipotence", "resurgence", "cataclysmic", "invincible",
    "apocalypse", "supernova", "singularity", "constellation",
    "dominion", "radiance", "omniscience", "ascendancy",
    "revelation", "primordial", "celestial", "unstoppable",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
