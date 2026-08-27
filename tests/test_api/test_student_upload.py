import io

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
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _first_course_id(client, headers: dict[str, str]) -> str:
    # Ensure mock semester exists via QA/dashboard side-effect path.
    courses = await client.get("/api/v1/student/courses", headers=headers)
    assert courses.status_code == 200
    payload = courses.json()
    assert payload, "Expected demo student to have enrollments"
    return payload[0]["id"]


@pytest.mark.asyncio
async def test_student_can_upload_and_delete_notes(client):
    headers = await _login_student(client)
    course_id = await _first_course_id(client, headers)

    content = (
        b"# My SSA notes\n\n"
        b"Pomodoro blocks help me finish Weekly Commitment Map tasks.\n\n"
        b"## Lab prep\n\n"
        b"Practice array reverse before PRF192 lab.\n"
    )

    upload = await client.post(
        f"/api/v1/student/courses/{course_id}/documents",
        headers=headers,
        files={"file": ("my_notes.md", io.BytesIO(content), "text/markdown")},
        data={"title": "My study notes"},
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["chunkCount"] >= 1
    assert body["source"] == "student_upload"
    document_id = body["id"]

    detail = await client.get(
        f"/api/v1/student/courses/{course_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    docs = detail.json()["documents"]
    mine = next(doc for doc in docs if doc["id"] == document_id)
    assert mine["canDelete"] is True
    assert mine["source"] == "student_upload"

    delete = await client.delete(
        f"/api/v1/student/courses/{course_id}/documents/{document_id}",
        headers=headers,
    )
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_student_upload_rejects_unsupported_type(client):
    headers = await _login_student(client)
    course_id = await _first_course_id(client, headers)

    response = await client.post(
        f"/api/v1/student/courses/{course_id}/documents",
        headers=headers,
        files={"file": ("notes.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert response.status_code == 400
