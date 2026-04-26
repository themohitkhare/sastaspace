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
            region.enemy_hp = (region.enemy_hp + regen).min(region.enemy_max_hp);
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
}
