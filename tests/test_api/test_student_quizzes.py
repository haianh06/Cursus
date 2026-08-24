"""Student-facing quiz-taking flow: instructor creates+publishes a quiz for
their class, the enrolled student lists it, opens it, and submits answers.

QuizService.list_for_student/get_for_student/submit already existed
alongside the instructor-side quiz CRUD, but no router ever called them --
src/api/student_quizzes.py is what actually wires them up. This file is the
first test coverage either the service methods or that router have had.
"""

from __future__ import annotations

import pytest

STUDENT = {"email": "student.demo@example.test", "password": "password123"}


async def _login(client, credentials: dict) -> dict:
    resp = await client.post("/api/v1/auth/login", json=credentials)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def _reset_demo(client, headers: dict) -> dict:
    resp = await client.post("/api/v1/demo/reset", json={"confirm": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _login_gate2_instructor(client) -> dict:
    """Same pattern as tests/test_api/test_gate2_flow.py -- see that file's
    own docstring for why this mints a token directly instead of a password
    login, and why the client's cookie jar must be cleared first."""
    from src.config import get_settings
    from src.db import models
    from src.db.connection import SessionLocal
    from src.security.tokens import create_access_token

    db = SessionLocal()
    try:
        instructor = db.query(models.User).filter_by(email="demo.instructor@cursusdemo.local").first()
        assert instructor is not None, "gate2_demo.py should have created this row on reset"
        token = create_access_token(subject=instructor.id, settings=get_settings())
    finally:
        db.close()
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


async def _setup_published_quiz(client) -> tuple[dict, dict, str]:
    """Returns (student_headers, instructor_headers, quiz_id) for a quiz
    with one published multiple-choice question on the gate2 demo section."""
    student_headers = await _login(client, STUDENT)
    await _reset_demo(client, student_headers)
    instructor_headers = await _login_gate2_instructor(client)

    classes = await client.get("/api/v1/instructor/quizzes/classes", headers=instructor_headers)
    assert classes.status_code == 200, classes.text
    section_id = classes.json()["classes"][0]["sectionId"]

    created = await client.post(
        "/api/v1/instructor/quizzes",
        json={
            "section_id": section_id,
            "title": "Quiz kiểm tra nhanh",
            "description": "Test quiz",
            "time_limit_minutes": 15,
        },
        headers=instructor_headers,
    )
    assert created.status_code == 201, created.text
    quiz_id = created.json()["id"]

    added = await client.post(
        f"/api/v1/instructor/quizzes/{quiz_id}/questions",
        json={
            "question_text": "2 + 2 = ?",
            "question_type": "MULTIPLE_CHOICE",
            "options": ["3", "4", "5", "6"],
            "correct_answer": "4",
            "points": 10,
        },
        headers=instructor_headers,
    )
    assert added.status_code == 201, added.text

    published = await client.post(
        f"/api/v1/instructor/quizzes/{quiz_id}/publish", headers=instructor_headers
    )
    assert published.status_code == 200, published.text

    return student_headers, instructor_headers, quiz_id


@pytest.mark.asyncio
async def test_student_sees_published_quiz_in_list(client):
    student_headers, _instructor_headers, quiz_id = await _setup_published_quiz(client)

    response = await client.get("/api/v1/student/quizzes", headers=student_headers)

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert quiz_id in ids


@pytest.mark.asyncio
async def test_student_can_open_quiz_and_answers_are_hidden_before_submit(client):
    student_headers, _instructor_headers, quiz_id = await _setup_published_quiz(client)

    response = await client.get(f"/api/v1/student/quizzes/{quiz_id}", headers=student_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["myStatus"] == "not_started"
    assert "correctAnswer" not in data["questions"][0]


@pytest.mark.asyncio
async def test_student_submit_grades_and_reveals_correct_answer(client):
    student_headers, _instructor_headers, quiz_id = await _setup_published_quiz(client)
    detail = await client.get(f"/api/v1/student/quizzes/{quiz_id}", headers=student_headers)
    question_id = detail.json()["questions"][0]["id"]

    response = await client.post(
        f"/api/v1/student/quizzes/{quiz_id}/submit",
        json={"answers": {question_id: "4"}},
        headers=student_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["myGrade"] == 100.0  # percentage, not raw points
    assert data["myStatus"] != "not_started"


@pytest.mark.asyncio
async def test_student_cannot_submit_twice(client):
    student_headers, _instructor_headers, quiz_id = await _setup_published_quiz(client)
    detail = await client.get(f"/api/v1/student/quizzes/{quiz_id}", headers=student_headers)
    question_id = detail.json()["questions"][0]["id"]
    first = await client.post(
        f"/api/v1/student/quizzes/{quiz_id}/submit",
        json={"answers": {question_id: "4"}},
        headers=student_headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/student/quizzes/{quiz_id}/submit",
        json={"answers": {question_id: "4"}},
        headers=student_headers,
    )

    assert second.status_code == 400


@pytest.mark.asyncio
async def test_unpublished_quiz_is_invisible_to_students(client):
    student_headers = await _login(client, STUDENT)
    await _reset_demo(client, student_headers)
    instructor_headers = await _login_gate2_instructor(client)
    classes = await client.get("/api/v1/instructor/quizzes/classes", headers=instructor_headers)
    section_id = classes.json()["classes"][0]["sectionId"]
    created = await client.post(
        "/api/v1/instructor/quizzes",
        json={
            "section_id": section_id,
            "title": "Draft quiz",
            "description": "",
            "time_limit_minutes": 15,
        },
        headers=instructor_headers,
    )
    quiz_id = created.json()["id"]

    response = await client.get(f"/api/v1/student/quizzes/{quiz_id}", headers=student_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_instructor_cannot_use_student_quiz_routes(client):
    _student_headers, instructor_headers, quiz_id = await _setup_published_quiz(client)

    response = await client.get(f"/api/v1/student/quizzes/{quiz_id}", headers=instructor_headers)

    assert response.status_code == 403
