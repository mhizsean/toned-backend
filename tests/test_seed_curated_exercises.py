from app.models.exercise import Exercise
from app.scripts.seed_curated_exercises import merge_curated, normalize_name, to_payload


def test_normalize_name_ignores_punctuation():
    assert normalize_name("Hip Thrust (Barbell)") == "hip thrust barbell"
    assert normalize_name("push-up") == "push up"


def test_hip_thrust_payload_maps_to_upper_legs():
    payload = to_payload(
        {
            "name": "Hip Thrust (Barbell)",
            "category": "Glutes & Legs",
            "equipment": "Barbell",
            "repLabel": "reps",
            "muscles": ["Glutes", "Hamstrings", "Core"],
            "steps": ["Drive hips up"],
            "tips": ["Squeeze"],
            "mistakes": ["Overarching"],
        }
    )
    assert payload["id"] == "toned-hip-thrust-barbell"
    assert payload["body_part"] == "upper legs"
    assert payload["source"] == "toned-seed"
    assert payload["name"] == "Hip Thrust (Barbell)"


def test_merge_inserts_missing_hip_thrust(db_session):
    created, coached = merge_curated(
        db_session,
        [
            {
                "name": "Hip Thrust (Barbell)",
                "category": "Glutes & Legs",
                "equipment": "Barbell",
                "repLabel": "reps",
                "muscles": ["Glutes", "Hamstrings"],
                "steps": ["Drive hips up"],
                "tips": ["Squeeze glutes"],
                "mistakes": ["Hyperextending"],
            }
        ],
    )
    db_session.commit()

    assert created == 1
    assert coached == 0
    row = db_session.get(Exercise, "toned-hip-thrust-barbell")
    assert row is not None
    assert row.name == "Hip Thrust (Barbell)"
    assert row.body_part == "upper legs"
    assert row.tips == ["Squeeze glutes"]


def test_merge_overlays_coaching_on_name_match(db_session):
    db_session.add(
        Exercise(
            id="0662",
            name="push-up",
            category="chest",
            body_part="chest",
            equipment="body weight",
            muscles=["chest"],
            steps=["Lower and press"],
            tips=[],
            mistakes=[],
            is_custom=False,
            source="exercises-dataset",
        )
    )
    db_session.commit()

    created, coached = merge_curated(
        db_session,
        [
            {
                "name": "Push-Up",
                "category": "Upper Body",
                "equipment": "Bodyweight",
                "muscles": ["Chest"],
                "steps": ["Keep a plank"],
                "tips": ["Brace your core"],
                "mistakes": ["Hips sagging"],
            }
        ],
    )
    db_session.commit()

    assert created == 0
    assert coached == 1
    row = db_session.get(Exercise, "0662")
    assert row.name == "push-up"
    assert row.tips == ["Brace your core"]
    assert row.mistakes == ["Hips sagging"]
    assert row.steps == ["Lower and press"]
