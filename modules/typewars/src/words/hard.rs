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
