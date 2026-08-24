from datetime import datetime, timedelta

import pytest


async def _login_student(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_timetable_crud_self_study_block(client):
    headers = await _login_student(client)

    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    start = monday.replace(hour=18, minute=0)
    end = monday.replace(hour=19, minute=30)

    create_response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={
            "title": "Review PRF192 notes",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["kind"] == "SELF_STUDY"
    assert created["locked"] is False
    block_id = created["id"]

    get_response = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start}",
        headers=headers,
    )
    assert get_response.status_code == 200
    blocks = get_response.json()["blocks"]
    assert any(block["id"] == block_id for block in blocks)

    moved_start = start.replace(hour=20)
    moved_end = end.replace(hour=21, minute=30)
    patch_response = await client.patch(
        f"/api/v1/plans/timetable/blocks/{block_id}",
        headers=headers,
        json={
            "title": "Review PRF192 + exercises",
            "start": moved_start.isoformat(),
            "end": moved_end.isoformat(),
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["title"] == "Review PRF192 + exercises"

    delete_response = await client.delete(
        f"/api/v1/plans/timetable/blocks/{block_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    after_delete = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start}",
        headers=headers,
    )
    assert after_delete.status_code == 200
    assert all(block["id"] != block_id for block in after_delete.json()["blocks"])


@pytest.mark.asyncio
async def test_timetable_bootstrap_creates_class_and_self_study(client):
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    response = await client.post(
        f"/api/v1/plans/timetable/bootstrap?week_start={week_start}",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    kinds = {block["kind"] for block in payload["blocks"]}
    assert "CLASS" in kinds
    assert "SELF_STUDY" in kinds


@pytest.mark.asyncio
async def test_timetable_rejects_self_study_overlap_with_class(client):
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    bootstrap = await client.post(
        f"/api/v1/plans/timetable/bootstrap?week_start={week_start}",
        headers=headers,
    )
    assert bootstrap.status_code == 200
    class_block = next(
        block for block in bootstrap.json()["blocks"] if block["kind"] == "CLASS"
    )
    class_start = datetime.fromisoformat(class_block["start"])
    overlap_end = class_start + timedelta(minutes=45)

    response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={
            "title": "Illegal overlap",
            "start": class_start.isoformat(),
            "end": overlap_end.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "overlap" in response.json()["detail"].lower()
