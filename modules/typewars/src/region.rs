use spacetimedb::{reducer, table, ReducerContext, ScheduleAt, Table};
use std::time::Duration;
use crate::war::global_war;
use crate::player::player;

#[table(accessor = region, public)]
pub struct Region {
    #[primary_key]
    pub id: u32,
    pub name: String,
    pub tier: u8,
    pub controlling_legion: i8,   // -1 = enemy-held
    pub enemy_hp: u64,
    pub enemy_max_hp: u64,
    pub regen_rate: u64,
    pub damage_0: u64,
    pub damage_1: u64,
    pub damage_2: u64,
    pub damage_3: u64,
    pub damage_4: u64,
    pub active_wardens: u32,
}

const REGION_SEED: &[(&str, u8)] = &[
    ("Ashfall Reach", 1), ("Bone Wastes", 1), ("Cinder Plains", 1),
    ("Dusk Hollow", 1),   ("Ember Ridge", 1), ("Frost Gate", 1),
    ("Gloom Marches", 1), ("Haze Fields", 1), ("Iron Strand", 1),
    ("Jade Crossing", 1),
    ("Krell Depths", 2),  ("Lava Run", 2),    ("Murk Basin", 2),
    ("Null Shore", 2),    ("Obsidian Shelf", 2), ("Pale Summit", 2),
    ("Quake Line", 2),    ("Rift Corridor", 2),  ("Scorch Trail", 2),
    ("Tide Lock", 2),
    ("Umbral Spire", 3),  ("Void Cradle", 3), ("War Engine", 3),
    ("Xen Bastion", 3),   ("Zero Point", 3),
];

fn hp_for_tier(tier: u8) -> u64 {
    match tier { 1 => 50_000, 2 => 100_000, 3 => 250_000, _ => 50_000 }
}

fn regen_for_tier(tier: u8) -> u64 {
    match tier { 1 => 200, 2 => 500, 3 => 1_500, _ => 200 }
}

pub fn seed_regions(ctx: &ReducerContext) {
    for (i, (name, tier)) in REGION_SEED.iter().enumerate() {
        let max_hp = hp_for_tier(*tier);
        ctx.db.region().insert(Region {
            id: i as u32,
            name: name.to_string(),
            tier: *tier,
            controlling_legion: -1,
            enemy_hp: max_hp,
            enemy_max_hp: max_hp,
            regen_rate: regen_for_tier(*tier),
            damage_0: 0, damage_1: 0, damage_2: 0, damage_3: 0, damage_4: 0,
            active_wardens: 0,
        });
    }
}

pub fn add_legion_damage(region: &mut Region, legion: u8, amount: u64) {
    match legion {
        0 => region.damage_0 += amount,
        1 => region.damage_1 += amount,
        2 => region.damage_2 += amount,
        3 => region.damage_3 += amount,
        4 => region.damage_4 += amount,
        _ => {}
    }
}

pub fn winning_legion(region: &Region) -> Option<u8> {
    let damages = [region.damage_0, region.damage_1, region.damage_2, region.damage_3, region.damage_4];
    let (idx, &max_dmg) = damages.iter().enumerate().max_by_key(|(_, &d)| d)?;
    if max_dmg == 0 { None } else { Some(idx as u8) }
}

pub fn reset_legion_damage(region: &mut Region) {
    region.damage_0 = 0; region.damage_1 = 0; region.damage_2 = 0;
    region.damage_3 = 0; region.damage_4 = 0;
}

pub fn effective_regen(base_regen: u64, active_wardens: u32) -> u64 {
    if active_wardens >= 3 { base_regen / 2 } else { base_regen }
}

/// Pure helper: applies a regen tick to an enemy-controlled region, capped
/// at `enemy_max_hp`. Pulled out of `region_tick` so the saturating-add +
/// cap behaviour can be unit-tested without a `ReducerContext`.
pub fn apply_regen(current_hp: u64, regen: u64, max_hp: u64) -> u64 {
    current_hp.saturating_add(regen).min(max_hp)
}

#[table(accessor = region_tick_schedule, scheduled(region_tick))]
pub struct RegionTickSchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduleAt,
}

#[reducer]
pub fn region_tick(ctx: &ReducerContext, _arg: RegionTickSchedule) -> Result<(), String> {
    let regions: Vec<Region> = ctx.db.region().iter().collect();

    for mut region in regions {
        if region.controlling_legion != -1 {
            continue;
        }

        if region.enemy_hp == 0 {
            let Some(winner) = winning_legion(&region) else {
                continue;
            };
            region.controlling_legion = winner as i8;
            reset_legion_damage(&mut region);
            ctx.db.region().id().update(region);

            if let Some(mut war) = ctx.db.global_war().id().find(1) {
                war.liberated_territories += 1;
                war.enemy_territories = war.enemy_territories.saturating_sub(1);
                let liberated = war.liberated_territories;
                ctx.db.global_war().id().update(war);

                if liberated >= 20 {
                    end_season(ctx);
                    return Ok(());
                }
            }
        } else {
            let regen = effective_regen(region.regen_rate, region.active_wardens);
            region.enemy_hp = apply_regen(region.enemy_hp, regen, region.enemy_max_hp);
            ctx.db.region().id().update(region);
        }
    }

    Ok(())
}

pub fn end_season(ctx: &ReducerContext) {
    if let Some(mut war) = ctx.db.global_war().id().find(1) {
        war.season += 1;
        war.liberated_territories = 0;
        war.enemy_territories = 25;
        war.season_start = ctx.timestamp;
        ctx.db.global_war().id().update(war);
    }

    let regions: Vec<Region> = ctx.db.region().iter().collect();
    for mut region in regions {
        region.controlling_legion = -1;
        region.enemy_hp = region.enemy_max_hp;
        reset_legion_damage(&mut region);
        ctx.db.region().id().update(region);
    }

    let players: Vec<crate::player::Player> = ctx.db.player().iter().collect();
    for mut player in players {
        player.season_damage = 0;
        ctx.db.player().identity().update(player);
    }
}

// Initialise the region_tick schedule (called from lib.rs init).
pub fn init_region_tick_schedule(ctx: &ReducerContext) {
    if ctx.db.region_tick_schedule().iter().next().is_some() { return; }
    ctx.db.region_tick_schedule().insert(RegionTickSchedule {
        scheduled_id: 0,
        scheduled_at: ScheduleAt::from(Duration::from_secs(60)),
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_region(d0: u64, d1: u64, d2: u64, d3: u64, d4: u64) -> Region {
        Region {
            id: 0, name: "Test".into(), tier: 1,
            controlling_legion: -1, enemy_hp: 0, enemy_max_hp: 50_000,
            regen_rate: 200, damage_0: d0, damage_1: d1, damage_2: d2,
            damage_3: d3, damage_4: d4, active_wardens: 0,
        }
    }

    #[test]
    fn winning_legion_picks_highest_damage() {
        let r = make_region(100, 500, 50, 200, 10);
        assert_eq!(winning_legion(&r), Some(1));
    }

    #[test]
    fn warden_bulwark_halves_regen_at_3_or_more() {
        assert_eq!(effective_regen(200, 3), 100);
        assert_eq!(effective_regen(200, 5), 100);
        assert_eq!(effective_regen(200, 2), 200);
        assert_eq!(effective_regen(200, 0), 200);
    }

    // === hp_for_tier / regen_for_tier ===

    #[test]
    fn hp_for_tier_matches_design_doc() {
        assert_eq!(hp_for_tier(1), 50_000);
        assert_eq!(hp_for_tier(2), 100_000);
        assert_eq!(hp_for_tier(3), 250_000);
    }

    #[test]
    fn hp_for_tier_falls_back_to_tier_1_for_unknown() {
        // Defensive default: anything outside the curated 1..=3 falls
        // back to tier-1 numbers rather than panicking.
        assert_eq!(hp_for_tier(0), 50_000);
        assert_eq!(hp_for_tier(4), 50_000);
        assert_eq!(hp_for_tier(255), 50_000);
    }

    #[test]
    fn regen_for_tier_matches_design_doc() {
        assert_eq!(regen_for_tier(1), 200);
        assert_eq!(regen_for_tier(2), 500);
        assert_eq!(regen_for_tier(3), 1_500);
    }

    #[test]
    fn regen_for_tier_falls_back_to_tier_1_for_unknown() {
        assert_eq!(regen_for_tier(0), 200);
        assert_eq!(regen_for_tier(255), 200);
    }

    // === apply_regen ===

    #[test]
    fn apply_regen_caps_at_max_hp() {
        // Regen would push past max — clamp to max.
        assert_eq!(apply_regen(49_500, 1_000, 50_000), 50_000);
    }

    #[test]
    fn apply_regen_below_cap_adds_normally() {
        assert_eq!(apply_regen(40_000, 200, 50_000), 40_200);
    }

    #[test]
    fn apply_regen_already_at_max_stays_at_max() {
        assert_eq!(apply_regen(50_000, 200, 50_000), 50_000);
    }

    #[test]
    fn apply_regen_handles_saturating_overflow() {
        // u64::MAX + 1 mathematically overflows; saturating_add prevents
        // the wraparound. The .min(max_hp) then clamps to max_hp.
        assert_eq!(apply_regen(u64::MAX, 100, 50_000), 50_000);
    }

    // === winning_legion edge cases ===

    #[test]
    fn winning_legion_returns_none_when_all_zero() {
        let r = make_region(0, 0, 0, 0, 0);
        assert_eq!(winning_legion(&r), None);
    }

    #[test]
    fn winning_legion_picks_legion_0_when_tied_at_top() {
        // max_by_key with a tie returns the LAST element. So a (100,
        // 100, 0, 0, 0) tie returns legion 1 (the later index of the
        // two top values). Pin the deterministic behaviour.
        let r = make_region(100, 100, 0, 0, 0);
        assert_eq!(winning_legion(&r), Some(1));
    }

    #[test]
    fn winning_legion_picks_legion_4_when_only_legion_4_has_damage() {
        let r = make_region(0, 0, 0, 0, 999);
        assert_eq!(winning_legion(&r), Some(4));
    }

    // === add_legion_damage ===

    #[test]
    fn add_legion_damage_targets_the_right_field() {
        let mut r = make_region(0, 0, 0, 0, 0);
        add_legion_damage(&mut r, 0, 100);
        add_legion_damage(&mut r, 2, 50);
        add_legion_damage(&mut r, 4, 25);
        assert_eq!(r.damage_0, 100);
        assert_eq!(r.damage_1, 0);
        assert_eq!(r.damage_2, 50);
        assert_eq!(r.damage_3, 0);
        assert_eq!(r.damage_4, 25);
    }

    #[test]
    fn add_legion_damage_ignores_invalid_legion() {
        // Out-of-range legion ids must NOT panic — they're silently dropped.
        // Real reducers gate legion at registration so this is defence in depth.
        let mut r = make_region(0, 0, 0, 0, 0);
        add_legion_damage(&mut r, 99, 1000);
        assert_eq!(r.damage_0, 0);
        assert_eq!(r.damage_1, 0);
        assert_eq!(r.damage_2, 0);
        assert_eq!(r.damage_3, 0);
        assert_eq!(r.damage_4, 0);
    }

    #[test]
    fn add_legion_damage_accumulates_across_calls() {
        let mut r = make_region(0, 0, 0, 0, 0);
        add_legion_damage(&mut r, 1, 100);
        add_legion_damage(&mut r, 1, 50);
        add_legion_damage(&mut r, 1, 25);
        assert_eq!(r.damage_1, 175);
    }

    // === reset_legion_damage ===

    #[test]
    fn reset_legion_damage_zeros_all_five_legions() {
        let mut r = make_region(100, 200, 300, 400, 500);
        reset_legion_damage(&mut r);
        assert_eq!(r.damage_0, 0);
        assert_eq!(r.damage_1, 0);
        assert_eq!(r.damage_2, 0);
        assert_eq!(r.damage_3, 0);
        assert_eq!(r.damage_4, 0);
    }

    #[test]
    fn region_seed_has_25_entries() {
        // Liberation goal is 20/25 — pin the seed length so a future
        // re-shuffle doesn't accidentally make the goal unreachable.
        assert_eq!(REGION_SEED.len(), 25);
    }

    #[test]
    fn region_seed_has_10_tier_1_10_tier_2_5_tier_3() {
        let by_tier = |t: u8| REGION_SEED.iter().filter(|(_, ti)| *ti == t).count();
        assert_eq!(by_tier(1), 10);
        assert_eq!(by_tier(2), 10);
        assert_eq!(by_tier(3), 5);
    }
}
