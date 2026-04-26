pub const LEGION_NAMES: [&str; 5] = ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"];
pub const LEGION_COUNT: u8 = 5;

/// Multiplier ceiling: Surge (legion 3) gets 5.0, all others 3.0.
pub fn multiplier_cap(legion: u8) -> f32 {
    if legion == 3 { 5.0 } else { 3.0 }
}

/// Streak-based damage multiplier, capped per legion.
pub fn compute_multiplier(streak: u32, cap: f32) -> f32 {
    (1.0 + streak as f32 * 0.25).min(cap)
}

/// True when Ashborn (legion 0) hits their 10-word burst trigger.
pub fn ashborn_burst_active(legion: u8, streak: u32) -> bool {
    legion == 0 && streak > 0 && streak % 10 == 0
}

/// True when a Codex (legion 1) player with ≥90% accuracy rolls the ~14% injection nonce.
pub fn codex_can_inject_rare(legion: u8, hits: u32, misses: u32, nonce: u64) -> bool {
    if legion != 1 {
        return false;
    }
    let total = hits + misses;
    if total == 0 {
        return false;
    }
    hits as f32 / total as f32 >= 0.90 && nonce % 7 == 0
}

/// Final damage after multiplier and legion bonuses.
/// `streak` is post-increment (the value after this word hit).
pub fn compute_damage(base_damage: u64, multiplier: f32, streak: u32, legion: u8) -> u64 {
    let mut dmg = base_damage as f32 * multiplier;
    if ashborn_burst_active(legion, streak) {
        dmg *= 3.0;
    }
    dmg as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn surge_has_higher_multiplier_cap() {
        assert_eq!(multiplier_cap(3), 5.0_f32);
        assert_eq!(multiplier_cap(0), 3.0_f32);
        assert_eq!(multiplier_cap(1), 3.0_f32);
        assert_eq!(multiplier_cap(2), 3.0_f32);
        assert_eq!(multiplier_cap(4), 3.0_f32);
    }

    #[test]
    fn multiplier_grows_with_streak_and_caps() {
        assert!((compute_multiplier(0, 3.0) - 1.0).abs() < 0.001);
        assert!((compute_multiplier(1, 3.0) - 1.25).abs() < 0.001);
        assert!((compute_multiplier(4, 3.0) - 2.0).abs() < 0.001);
        assert!((compute_multiplier(8, 3.0) - 3.0).abs() < 0.001);
        assert!((compute_multiplier(100, 3.0) - 3.0).abs() < 0.001);
        assert!((compute_multiplier(16, 5.0) - 5.0).abs() < 0.001);
    }

    #[test]
    fn ashborn_burst_fires_at_10_20_not_9_or_11() {
        assert!(ashborn_burst_active(0, 10));
        assert!(ashborn_burst_active(0, 20));
        assert!(ashborn_burst_active(0, 30));
        assert!(!ashborn_burst_active(0, 9));
        assert!(!ashborn_burst_active(0, 11));
        assert!(!ashborn_burst_active(1, 10));
        assert!(!ashborn_burst_active(0, 0));
    }

    #[test]
    fn codex_rare_requires_90_percent_and_nonce_mod_7() {
        assert!(codex_can_inject_rare(1, 9, 1, 0));
        assert!(!codex_can_inject_rare(1, 8, 2, 0));
        assert!(!codex_can_inject_rare(0, 9, 1, 0));
        assert!(!codex_can_inject_rare(1, 9, 1, 1));
        assert!(!codex_can_inject_rare(1, 0, 0, 0));
    }

    #[test]
    fn damage_is_base_times_multiplier() {
        assert_eq!(compute_damage(10, 2.0, 5, 1), 20);
    }

    #[test]
    fn ashborn_triples_damage_at_streak_10() {
        assert_eq!(compute_damage(10, 3.0, 10, 0), 90);
    }
}
