from app.catalogue.access import has_full_catalogue_access
from app.catalogue.curation import (
    PROTECTED_IDS,
    assign_family,
    curate,
    is_public_catalogue_exercise,
    load_allowlist_ids,
    normalize_name,
)
from app.models.exercise import Exercise
from app.services.exercise_service import ExerciseService


def test_protected_ids_are_in_committed_allowlist():
    ids = load_allowlist_ids()
    assert PROTECTED_IDS <= ids
    assert 330 <= len(ids) <= 420


def test_assign_family_recognises_standard_movements():
    assert assign_family("barbell full squat") == "back_squat"
    assert assign_family("dumbbell goblet squat") == "goblet_squat"
    assert assign_family("walking lunge") == "walking_lunge"
    assert assign_family("push-up") == "push_up"


def test_curate_keeps_protected_and_drops_obscure(tmp_path=None):
    records = [
        {
            "id": "0662",
            "name": "push-up",
            "body_part": "chest",
            "equipment": "body weight",
        },
        {
            "id": "9999",
            "name": "back lever",
            "body_part": "back",
            "equipment": "body weight",
        },
        {
            "id": "8888",
            "name": "barbell bench press",
            "body_part": "chest",
            "equipment": "barbell",
        },
    ]
    result = curate(records)
    kept_ids = set(result.kept_ids)
    assert "0662" in kept_ids
    assert "8888" in kept_ids
    assert "9999" not in kept_ids


def test_is_public_catalogue_exercise_rules():
    allow = {"0662"}
    assert is_public_catalogue_exercise(
        exercise_id="0662", source="exercises-dataset", is_custom=False, allowlist=allow
    )
    assert not is_public_catalogue_exercise(
        exercise_id="0007", source="exercises-dataset", is_custom=False, allowlist=allow
    )
    assert is_public_catalogue_exercise(
        exercise_id="toned-hip-thrust-barbell",
        source="toned-seed",
        is_custom=False,
        allowlist=allow,
    )
    assert is_public_catalogue_exercise(
        exercise_id="my-move", source="custom", is_custom=True, allowlist=allow
    )


def test_full_catalogue_access_is_email_gated():
    assert has_full_catalogue_access("seanseun.ss@gmail.com")
    assert has_full_catalogue_access("SeanSeun.ss@gmail.com")
    assert not has_full_catalogue_access("other@example.com")
    assert not has_full_catalogue_access(None)


def test_list_exercises_hides_unpublished_dataset_rows(db_session):
    db_session.add_all(
        [
            Exercise(
                id="0662",
                name="push-up",
                category="chest",
                body_part="chest",
                equipment="body weight",
                muscles=["chest"],
                steps=["Lower"],
                tips=[],
                mistakes=[],
                is_custom=False,
                source="exercises-dataset",
            ),
            Exercise(
                id="0007",
                name="alternate lateral pulldown",
                category="back",
                body_part="back",
                equipment="cable",
                muscles=["lats"],
                steps=["Pull"],
                tips=[],
                mistakes=[],
                is_custom=False,
                source="exercises-dataset",
            ),
        ]
    )
    db_session.commit()

    rows, total = ExerciseService.list_exercises(db_session, limit=50)
    ids = {row.id for row in rows}
    assert "0662" in ids
    assert "0007" not in ids
    assert total == 1


def test_list_exercises_shows_full_catalogue_for_allowlisted_email(db_session):
    db_session.add_all(
        [
            Exercise(
                id="0662",
                name="push-up",
                category="chest",
                body_part="chest",
                equipment="body weight",
                muscles=["chest"],
                steps=["Lower"],
                tips=[],
                mistakes=[],
                is_custom=False,
                source="exercises-dataset",
            ),
            Exercise(
                id="0007",
                name="alternate lateral pulldown",
                category="back",
                body_part="back",
                equipment="cable",
                muscles=["lats"],
                steps=["Pull"],
                tips=[],
                mistakes=[],
                is_custom=False,
                source="exercises-dataset",
            ),
        ]
    )
    db_session.commit()

    rows, total = ExerciseService.list_exercises(
        db_session,
        viewer_email="seanseun.ss@gmail.com",
        limit=50,
    )
    ids = {row.id for row in rows}
    assert "0662" in ids
    assert "0007" in ids
    assert total == 2


def test_normalize_name_used_for_template_overlap():
    assert normalize_name("Glute Bridge") == "glute bridge"
    assert normalize_name("Dead Bug") == "dead bug"
