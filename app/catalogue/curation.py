"""Curate the 1,324-row third-party dataset down to a gym-useful subset.

Does not invent exercises. Keeps original IDs and rows. Session templates
are name-based and are not modified.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "data" / "exercises_dataset.json"
CURATED_PATH = ROOT / "data" / "exercises_seed.json"
TEMPLATES_PATH = ROOT / "data" / "session_templates_seed.json"
ALLOWLIST_PATH = ROOT / "data" / "exercises_catalogue_allowlist.json"

# Fixture IDs used in backend/frontend tests — keep so tests and stored
# library rows that reference them still resolve.
PROTECTED_IDS = {
    "0001",  # 3/4 sit-up
    "0002",  # 45° side bend
    "0042",  # barbell front squat
    "0276",  # dead bug
    "0662",  # push-up
    "1460",  # walking lunge
    "3013",  # low glute bridge on floor
}

# Most-specific patterns first. An exercise is assigned to the first match.
# cap = max variants to keep in that family (equipment / stance diversity).
FAMILY_RULES: tuple[tuple[str, tuple[str, ...], int], ...] = (
    # Legs / glutes
    ("bulgarian_split_squat", ("bulgarian",), 3),
    ("split_squat", ("split squat", "split squats"), 3),
    ("front_squat", ("front squat",), 2),
    ("goblet_squat", ("goblet squat", "goblet"), 2),
    ("hack_squat", ("hack squat",), 2),
    ("pistol_squat", ("pistol squat", "pistol"), 1),
    ("jump_squat", ("jump squat", "squat jump"), 1),
    ("sumo_squat", ("sumo squat",), 2),
    ("sissy_squat", ("sissy squat",), 1),
    ("box_squat", ("box squat",), 1),
    ("wall_sit", ("wall sit", "wall squat"), 1),
    ("overhead_squat", ("overhead squat",), 1),
    ("cossack_squat", ("cossack",), 1),
    ("back_squat", ("back squat", "full squat", "high bar squat", "low bar squat", "smith squat", "smith full squat"), 4),
    ("bodyweight_squat", ("bodyweight squat", "dumbbell squat", "weighted squat", "squat"), 3),
    ("curtsy_lunge", ("curtsy", "curtsey"), 1),
    ("lateral_lunge", ("lateral lunge", "side lunge"), 2),
    ("reverse_lunge", ("reverse lunge",), 2),
    ("walking_lunge", ("walking lunge",), 2),
    ("jumping_lunge", ("jumping lunge", "lunge jump"), 1),
    ("lunge", ("lunge",), 4),
    ("leg_press", ("leg press",), 3),
    ("leg_extension", ("leg extension",), 2),
    ("seated_leg_curl", ("seated leg curl", "seated hamstring"), 2),
    ("lying_leg_curl", ("lying leg curl", "lying hamstring", "prone leg curl"), 2),
    ("standing_leg_curl", ("standing leg curl", "standing hamstring"), 1),
    ("nordic_curl", ("nordic",), 1),
    ("good_morning", ("good morning",), 2),
    ("single_leg_rdl", ("single leg rdl", "single-leg romanian", "single leg romanian", "one leg romanian"), 2),
    ("rdl", ("romanian deadlift", "rdl", "stiff leg", "stiff-leg"), 3),
    ("sumo_deadlift", ("sumo deadlift",), 2),
    ("trap_bar_deadlift", ("trap bar", "hex bar"), 1),
    ("deadlift", ("deadlift",), 3),
    ("hip_thrust", ("hip thrust",), 3),
    ("single_leg_glute_bridge", ("single leg glute", "one leg glute", "single-leg glute"), 2),
    ("glute_bridge", ("glute bridge", "bridge on floor"), 2),
    ("cable_kickback", ("kickback", "donkey kick"), 2),
    ("pull_through", ("pull through", "pull-through"), 1),
    ("hip_abduction", ("hip abduction", "abductor"), 2),
    ("hip_adduction", ("hip adduction", "adductor"), 2),
    ("clamshell", ("clamshell", "clam shell"), 1),
    ("fire_hydrant", ("fire hydrant",), 1),
    ("step_up", ("step up", "step-up", "stepup"), 2),
    ("standing_calf_raise", ("standing calf",), 2),
    ("seated_calf_raise", ("seated calf",), 2),
    ("donkey_calf", ("donkey calf",), 1),
    ("calf_raise", ("calf raise", "calf press"), 2),
    # Chest
    ("incline_bench_press", ("incline bench press", "incline press"), 4),
    ("decline_bench_press", ("decline bench press", "decline press"), 3),
    ("bench_press", ("bench press",), 4),
    ("machine_chest_press", ("chest press",), 2),
    ("incline_chest_fly", ("incline fly", "incline cable fly", "incline dumbbell fly"), 2),
    ("chest_fly", ("chest fly", "pec deck", "pec fly", "dumbbell fly", "cable fly", "crossover", "cable crossover", "butterfly"), 4),
    ("diamond_push_up", ("diamond push",), 1),
    ("decline_push_up", ("decline push",), 1),
    ("incline_push_up", ("incline push",), 1),
    ("archer_push_up", ("archer push",), 1),
    ("push_up", ("push-up", "push up", "pushup"), 3),
    ("bench_dip", ("bench dip",), 1),
    ("chest_dip", ("chest dip", "parallel bar dip", "tricep dip", "triceps dip", "dip"), 2),
    ("pullover", ("pullover",), 2),
    # Back
    ("archer_pull_up", ("archer pull",), 1),
    ("chin_up", ("chin-up", "chin up", "chinup"), 2),
    ("pull_up", ("pull-up", "pull up", "pullup"), 3),
    ("close_grip_pulldown", ("close grip pulldown", "close-grip pulldown", "close grip lat"), 2),
    ("lat_pulldown", ("lat pulldown", "pulldown", "lateral pulldown"), 4),
    ("straight_arm_pulldown", ("straight arm pulldown", "straight-arm pulldown", "straight arm pushdown"), 1),
    ("face_pull", ("face pull",), 1),
    ("seated_cable_row", ("seated row", "seated cable row", "cable seated row", "low seated row"), 3),
    ("one_arm_row", ("one arm row", "single arm row", "one-arm row", "dumbbell row"), 3),
    ("t_bar_row", ("t-bar", "t bar", "tbar"), 2),
    ("pendlay_row", ("pendlay",), 1),
    ("chest_supported_row", ("chest supported", "chest-supported"), 1),
    ("inverted_row", ("inverted row", "australian", "bodyweight standing row", "bench pull"), 2),
    ("bent_over_row", ("bent over row", "bent-over row", "barbell row"), 3),
    ("row", ("row",), 3),
    ("shrug", ("shrug",), 3),
    ("back_extension", ("back extension", "hyperextension"), 2),
    ("glute_ham_raise", ("glute-ham", "glute ham"), 1),
    ("superman", ("superman",), 1),
    # Shoulders
    ("arnold_press", ("arnold",), 1),
    ("push_press", ("push press",), 1),
    ("shoulder_press", ("shoulder press", "overhead press", "military press", "overhead shoulder"), 4),
    ("landmine_press", ("landmine",), 2),
    ("lateral_raise", ("lateral raise", "side raise", "side lateral"), 4),
    ("front_raise", ("front raise",), 3),
    ("rear_delt_fly", ("rear delt", "reverse fly", "reverse pec", "bent over lateral"), 3),
    ("upright_row", ("upright row",), 2),
    # Arms
    ("hammer_curl", ("hammer curl",), 3),
    ("preacher_curl", ("preacher",), 3),
    ("concentration_curl", ("concentration",), 1),
    ("incline_curl", ("incline curl", "incline dumbbell curl"), 2),
    ("reverse_curl", ("reverse curl",), 1),
    ("spider_curl", ("spider curl",), 1),
    ("cable_curl", ("cable curl", "cable bicep"), 2),
    ("barbell_curl", ("barbell curl", "ez bar curl", "ez barbell curl"), 3),
    ("dumbbell_curl", ("dumbbell curl", "bicep curl", "biceps curl"), 3),
    ("curl", ("curl",), 3),
    ("skull_crusher", ("skull crusher", "lying tricep", "lying triceps", "french press"), 3),
    ("tricep_pushdown", ("pushdown", "push-down", "pressdown"), 3),
    ("overhead_tricep", ("overhead tricep", "overhead triceps", "overhead extension"), 3),
    ("tricep_kickback", ("tricep kickback", "triceps kickback"), 2),
    ("close_grip_bench", ("close grip bench", "close-grip bench"), 1),
    ("tricep_extension", ("tricep extension", "triceps extension"), 3),
    ("wrist_curl", ("wrist curl", "wrist extension", "reverse wrist"), 3),
    # Core
    ("side_plank", ("side plank",), 1),
    ("plank", ("plank",), 3),
    ("dead_bug", ("dead bug",), 1),
    ("bird_dog", ("bird dog",), 1),
    ("bicycle_crunch", ("bicycle",), 1),
    ("reverse_crunch", ("reverse crunch",), 1),
    ("cable_crunch", ("cable crunch",), 1),
    ("crunch", ("crunch",), 3),
    ("sit_up", ("sit-up", "sit up", "situp"), 2),
    ("hanging_leg_raise", ("hanging leg", "hanging knee"), 2),
    ("lying_leg_raise", ("lying leg raise", "leg raise", "knee raise"), 3),
    ("russian_twist", ("russian twist",), 2),
    ("woodchop", ("woodchop", "wood chop", "chop"), 2),
    ("pallof", ("pallof",), 2),
    ("ab_rollout", ("rollout", "ab wheel", "wheel rollout"), 1),
    ("mountain_climber", ("mountain climber",), 1),
    ("hollow_hold", ("hollow",), 1),
    ("v_up", ("v-up", "v up", "vup"), 1),
    ("flutter_kick", ("flutter",), 1),
    ("heel_touch", ("heel touch",), 1),
    ("toe_touch", ("toe touch",), 1),
    ("side_bend", ("side bend",), 2),
    # Cardio / conditioning
    ("kettlebell_swing", ("kettlebell swing", "kb swing"), 1),
    ("turkish_get_up", ("turkish", "get-up", "get up"), 1),
    ("thruster", ("thruster",), 1),
    ("power_clean", ("power clean", "clean"), 1),
    ("farmers_walk", ("farmer",), 1),
    ("sled", ("sled", "prowler"), 1),
    ("bear_crawl", ("bear crawl",), 1),
    ("burpee", ("burpee",), 1),
    ("box_jump", ("box jump",), 1),
    ("jump_rope", ("jump rope", "skipping"), 1),
    ("jumping_jack", ("jumping jack",), 1),
    ("high_knees", ("high knee",), 1),
    ("skater", ("skater",), 1),
    ("run", ("run", "sprint"), 2),
    ("walk", ("walk", "treadmill"), 2),
    ("bike", ("bike", "cycle", "assault"), 1),
    ("elliptical", ("elliptical",), 1),
    ("stepmill", ("stepmill", "stair", "step mill"), 1),
    ("ski_erg", ("ski",), 1),
    ("inchworm", ("inchworm",), 1),
    # Mobility
    ("child_pose", ("child",), 1),
    ("cat_cow", ("cat cow", "cat-cow", "cat camel"), 1),
    ("hip_flexor_stretch", ("hip flexor",), 1),
    ("pigeon", ("pigeon",), 1),
    ("figure_four", ("figure four", "figure 4"), 1),
    ("hamstring_stretch", ("hamstring stretch",), 1),
    ("quad_stretch", ("quad stretch", "quadriceps stretch"), 1),
    ("chest_stretch", ("chest stretch", "doorway", "chest opener"), 1),
    ("shoulder_stretch", ("shoulder stretch", "cross body"), 1),
    ("neck_stretch", ("neck",), 2),
    ("forward_fold", ("forward fold", "forward bend"), 1),
    ("cobra", ("cobra",), 1),
    ("downward_dog", ("downward",), 1),
    ("worlds_greatest", ("world",), 1),
    ("stretch", ("stretch",), 8),
)

HARD_REJECT_RE = (
    r"\bv\s*[2-5]\b",
    r"with towel",
    r"\bbosu\b",
    r"\bpartner\b",
    r"self assisted",
    r"stability ball",
    r"exercise ball",
    r"swiss ball",
    r"front lever",
    r"back lever",
    r"human flag",
    r"\bplanche\b",
    r"skin the cat",
    r"guillotine",
    r"jefferson",
    r"\bsots\b",
    r"split jerk",
    r"power snatch",
    r"muscle snatch",
    r"hang clean",
    r"clean pull",
    r"snatch pull",
    r"jack burpee",
    r"\bmale\b",
    r"\bfemale\b",
    r"bottoms up",
    r"around the world",
    r"one arm twisting",
    r"kneeling one arm",
    r"with rope attachment",
    r"full range of motion",
    r"pro lat bar",
    r"palm rotational",
    r"olympic barbell",
    r"on knees",
    r"\bpov\b",
    r"arm blaster",
    r"hyght",
    r"squat jerk",
    r"potty squat",
    r"frankenstein",
    r"with run release",
    r"power point",
    r"around world",
    r"box jump down",
    r"squatting row",
    r"squatting curl",
    r"bench squat",
    r"squat row",
    r"curl squat",
    r"skier\b",
    r"finger curl",
    r"three bench",
    r"sitted",
    r"zercher",
    r"speed squat",
    r"plyo squat",
    r"supported squat",
    r"contralateral",
    r"front chest squat",
    r"clean grip front",
    r"bench front squat",
    r"reverse grip decline",
    r"wide reverse grip",
    r"twisting bench",
    r"squat jump step",
    r"kneeling jump",
    r"narrow stance squat",
    r"one leg squat",
    r"\bjm\b",
    r"full can",
    r"palms in",
    r"medicine ball chest",
    r"deep push up",
    r"high knee against",
    r"crab twist",
    r"twisted leg raise",
    r"barbell press sit",
    r"all fours squad",
)

QUALITY_PENALTY = (
    "kneeling",
    "one arm",
    "single arm",
    "alternate",
    "twisting",
    "on bench",
    "incline bench",
    "with chain",
    "wide grip",
    "reverse grip",
    "underhand",
    "behind head",
    "behind neck",
    "with support",
    "parallel grip",
    "close grip off",
    "drop jump",
)

BODY_PART_QUOTA = {
    "upper arms": 50,
    "upper legs": 90,
    "back": 58,
    "chest": 42,
    "shoulders": 45,
    "waist": 38,
    "lower legs": 15,
    "lower arms": 8,
    "cardio": 15,
    "neck": 2,
}

EQUIP_RANK = {
    "barbell": 1,
    "ez barbell": 2,
    "dumbbell": 3,
    "cable": 4,
    "body weight": 5,
    "kettlebell": 6,
    "leverage machine": 7,
    "smith machine": 8,
    "trap bar": 3,
    "band": 10,
    "resistance band": 9,
    "weighted": 9,
    "assisted": 8,
    "medicine ball": 11,
    "sled machine": 6,
    "rope": 5,
    "stationary bike": 5,
    "elliptical machine": 5,
    "stepmill machine": 5,
    "skierg machine": 5,
    "tire": 7,
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def load_json(path: Path) -> list | dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _protected_names() -> set[str]:
    names: set[str] = set()
    if CURATED_PATH.exists():
        for item in load_json(CURATED_PATH):
            names.add(normalize_name(item["name"]))
    if TEMPLATES_PATH.exists():
        for template in load_json(TEMPLATES_PATH):
            for exercise in template.get("exercises") or []:
                names.add(normalize_name(exercise["name"]))
    names.update(
        {
            "glute bridge",
            "glute bridge bodyweight",
            "cat cow",
            "cat cow stretch",
            "hip flexor stretch",
            "neck side stretch",
            "dead bug",
            "bird dog",
            "plank",
            "child s pose",
            "treadmill",
            "incline treadmill walk",
            "assault bike",
            "stairmaster",
            "push up",
            "walking lunge",
            "barbell front squat",
        }
    )
    return names


def assign_family(name: str) -> str | None:
    n = normalize_name(name)
    for family, patterns, _cap in FAMILY_RULES:
        for pattern in patterns:
            if pattern in n:
                return family
    return None


def family_cap(family: str) -> int:
    for name, _patterns, cap in FAMILY_RULES:
        if name == family:
            return cap
    return 1


def hard_reject_reason(name: str) -> str | None:
    n = normalize_name(name)
    for pattern in HARD_REJECT_RE:
        if re.search(pattern, n):
            return f"obscure or duplicate naming: {pattern}"
    return None


def _variant_penalty(name: str) -> int:
    n = normalize_name(name)
    penalty = 0
    for token in QUALITY_PENALTY:
        if token in n:
            penalty += 1
    penalty += max(0, len(n.split()) - 6)
    return penalty


@dataclass
class CurateResult:
    kept: list[dict]
    removed: list[dict]
    groups: int
    borderline: list[dict] = field(default_factory=list)

    @property
    def kept_ids(self) -> list[str]:
        return [item["id"] for item in self.kept]


def curate(records: list[dict]) -> CurateResult:
    protected_names = _protected_names()
    kept: list[dict] = []
    removed: list[dict] = []
    families: dict[str, list[dict]] = defaultdict(list)
    borderline: list[dict] = []

    for item in records:
        n = normalize_name(item["name"])
        protected = item["id"] in PROTECTED_IDS or n in protected_names
        if not protected:
            reason = hard_reject_reason(item["name"])
            if reason:
                removed.append({**item, "remove_reason": reason})
                continue
        family = assign_family(item["name"])
        if family is None and not protected:
            removed.append(
                {
                    **item,
                    "remove_reason": "not a commonly recognised gym movement",
                }
            )
            continue
        families[family or f"protected:{item['id']}"].append(item)

    for family, members in families.items():
        members_sorted = sorted(
            members,
            key=lambda item: (
                0 if item["id"] in PROTECTED_IDS else 1,
                0 if normalize_name(item["name"]) in protected_names else 1,
                EQUIP_RANK.get((item.get("equipment") or "").lower(), 15),
                _variant_penalty(item["name"]),
                len(item["name"]),
                item["name"].lower(),
            ),
        )
        cap = family_cap(family) if not family.startswith("protected:") else 1
        selected: list[dict] = []
        seen_equip: set[str] = set()
        for item in members_sorted:
            equip = (item.get("equipment") or "").lower()
            forced = (
                item["id"] in PROTECTED_IDS
                or normalize_name(item["name"]) in protected_names
            )
            if forced:
                selected.append(item)
                seen_equip.add(equip)
                continue
            if len(selected) >= cap:
                removed.append(
                    {
                        **item,
                        "remove_reason": f"redundant variation of '{family}'",
                    }
                )
                continue
            if equip in seen_equip and family not in {
                "bench_press",
                "incline_bench_press",
                "row",
                "bent_over_row",
                "lat_pulldown",
                "curl",
                "lunge",
                "squat",
                "back_squat",
                "deadlift",
                "rdl",
                "shoulder_press",
                "chest_fly",
                "lateral_raise",
                "push_up",
            }:
                removed.append(
                    {
                        **item,
                        "remove_reason": f"same equipment already kept for '{family}'",
                    }
                )
                continue
            selected.append(item)
            seen_equip.add(equip)
            if _variant_penalty(item["name"]) >= 2:
                borderline.append(item)
        kept.extend(selected)

    target = 380
    fill_pool = [
        item
        for item in removed
        if str(item.get("remove_reason", "")).startswith("redundant")
        or "same equipment already kept" in str(item.get("remove_reason", ""))
    ]
    fill_pool.sort(
        key=lambda item: (
            EQUIP_RANK.get((item.get("equipment") or "").lower(), 15),
            _variant_penalty(item["name"]),
            len(item["name"]),
        )
    )
    kept_ids = {item["id"] for item in kept}
    used_fill: set[str] = set()
    for item in fill_pool:
        if len(kept) >= target:
            break
        if item["id"] in kept_ids:
            continue
        if _variant_penalty(item["name"]) > 1:
            continue
        if len(normalize_name(item["name"]).split()) > 6:
            continue
        kept.append(item)
        kept_ids.add(item["id"])
        used_fill.add(item["id"])
        borderline.append(item)
    if used_fill:
        removed = [item for item in removed if item["id"] not in used_fill]

    # Rebalance so one muscle group (especially curls) cannot dominate.
    by_part: dict[str, list[dict]] = defaultdict(list)
    for item in kept:
        by_part[item.get("body_part") or "unknown"].append(item)
    trimmed: list[dict] = []
    for part, members in by_part.items():
        quota = BODY_PART_QUOTA.get(part, len(members))
        members_sorted = sorted(
            members,
            key=lambda item: (
                0 if item["id"] in PROTECTED_IDS else 1,
                0 if normalize_name(item["name"]) in protected_names else 1,
                _variant_penalty(item["name"]),
                len(item["name"]),
            ),
        )
        keep_part = members_sorted[:quota]
        drop_part = members_sorted[quota:]
        trimmed.extend(keep_part)
        for item in drop_part:
            removed.append(
                {
                    **item,
                    "remove_reason": f"over-quota for {part}",
                }
            )
    kept = trimmed

    # Fill body parts that are still short using leftover family variants.
    kept_ids = {item["id"] for item in kept}
    underfill_ids: set[str] = set()
    for part, quota in BODY_PART_QUOTA.items():
        have = sum(1 for item in kept if item.get("body_part") == part)
        if have >= quota:
            continue
        pool = [
            item
            for item in removed
            if item.get("body_part") == part
            and item["id"] not in kept_ids
            and (
                str(item.get("remove_reason", "")).startswith("redundant")
                or "same equipment already kept" in str(item.get("remove_reason", ""))
                or str(item.get("remove_reason", "")).startswith("over-quota")
            )
            and _variant_penalty(item["name"]) <= 2
            and len(normalize_name(item["name"]).split()) <= 7
        ]
        pool.sort(
            key=lambda item: (
                _variant_penalty(item["name"]),
                EQUIP_RANK.get((item.get("equipment") or "").lower(), 15),
                len(item["name"]),
            )
        )
        for item in pool:
            if have >= quota:
                break
            kept.append(item)
            kept_ids.add(item["id"])
            underfill_ids.add(item["id"])
            have += 1
            borderline.append(item)
    if underfill_ids:
        removed = [item for item in removed if item["id"] not in underfill_ids]

    kept.sort(key=lambda item: (item.get("body_part") or "", item["name"].lower()))
    return CurateResult(
        kept=kept,
        removed=removed,
        groups=len(families),
        borderline=borderline,
    )


def write_allowlist(
    result: CurateResult,
    source_count: int,
    path: Path = ALLOWLIST_PATH,
) -> None:
    payload = {
        "source_count": source_count,
        "kept_count": len(result.kept),
        "removed_count": len(result.removed),
        "duplicate_groups": result.groups,
        "ids": result.kept_ids,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path = path.with_name("exercises_catalogue_removed.json")
    report = [
        {
            "id": item["id"],
            "name": item["name"],
            "body_part": item.get("body_part"),
            "equipment": item.get("equipment"),
            "reason": item.get("remove_reason"),
        }
        for item in result.removed
    ]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def load_allowlist_ids(path: Path = ALLOWLIST_PATH) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("ids") or [])


def is_public_catalogue_exercise(
    *,
    exercise_id: str,
    source: str | None,
    is_custom: bool,
    allowlist: set[str] | None = None,
) -> bool:
    if is_custom:
        return True
    if (source or "") == "toned-seed":
        return True
    if exercise_id.startswith("toned-"):
        return True
    ids = allowlist if allowlist is not None else load_allowlist_ids()
    return exercise_id in ids
