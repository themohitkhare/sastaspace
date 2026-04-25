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
    "kinesis", "liberate", "monarch", "nuclear", "oblique",
    "phantom", "quantum", "rapture", "sanctum", "tempest",
    "unknown", "vagrant", "warfare", "xenolith", "yeoman",
    "abandon", "barrage", "crusade", "destiny", "eternal",
];

pub fn select(nonce: u64) -> &'static str {
    WORDS[nonce as usize % WORDS.len()]
}
