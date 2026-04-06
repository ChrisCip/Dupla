import pytest


@pytest.mark.asyncio
async def test_admin_list_users_master_ok(client, auth_headers_async: dict[str, str]):
    res = await client.get("/api/admin/users", headers=auth_headers_async)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    emails = {u["email"] for u in body}
    assert "tester@dupla.demo" in emails
    assert "worker@dupla.demo" in emails


@pytest.mark.asyncio
async def test_admin_forbidden_for_worker(client):
    res = await client.post(
        "/api/auth/token",
        data={"username": "worker@dupla.demo", "password": "workerpass123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/admin/users", headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_user(client, auth_headers_async: dict[str, str]):
    res = await client.post(
        "/api/admin/users",
        headers={**auth_headers_async, "Content-Type": "application/json"},
        json={
            "email": "newuser@dupla.demo",
            "password": "longpassword1",
            "role": "WORKER",
            "module_ids": [1],
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["email"] == "newuser@dupla.demo"


@pytest.mark.asyncio
async def test_chat_flow(client, auth_headers_async: dict[str, str]):
    empty = await client.get("/api/chat/messages", headers=auth_headers_async)
    assert empty.status_code == 200
    assert empty.json() == []

    post = await client.post(
        "/api/chat/messages",
        headers={**auth_headers_async, "Content-Type": "application/json"},
        json={"body": "Hola equipo"},
    )
    assert post.status_code == 201, post.text
    msg = post.json()
    assert msg["body"] == "Hola equipo"
    mid = msg["uuid"]

    again = await client.get("/api/chat/messages", headers=auth_headers_async)
    assert again.status_code == 200
    assert len(again.json()) == 1

    after = await client.get(f"/api/chat/messages?after_uuid={mid}", headers=auth_headers_async)
    assert after.status_code == 200
    assert after.json() == []


@pytest.mark.asyncio
async def test_task_board_master_read_only(client, auth_headers_async: dict[str, str]):
    board = await client.get("/api/tasks/board", headers=auth_headers_async)
    assert board.status_code == 200
    lists = board.json()["lists"]
    assert len(lists) == 3

    list_uuid = lists[0]["uuid"]
    create = await client.post(
        "/api/tasks/cards",
        headers={**auth_headers_async, "Content-Type": "application/json"},
        json={"list_uuid": str(list_uuid), "title": "Tarea demo"},
    )
    assert create.status_code == 403


@pytest.mark.asyncio
async def test_task_board_worker_create_and_move(client):
    res = await client.post(
        "/api/auth/token",
        data={"username": "worker@dupla.demo", "password": "workerpass123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    board = await client.get("/api/tasks/board", headers=headers)
    assert board.status_code == 200
    lists = board.json()["lists"]
    a, b = lists[0]["uuid"], lists[1]["uuid"]

    create = await client.post(
        "/api/tasks/cards",
        headers={**headers, "Content-Type": "application/json"},
        json={"list_uuid": str(a), "title": "Moverme"},
    )
    assert create.status_code == 201, create.text
    card_id = create.json()["uuid"]

    patch = await client.patch(
        f"/api/tasks/cards/{card_id}",
        headers={**headers, "Content-Type": "application/json"},
        json={"list_uuid": str(b), "position": 0},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["list_uuid"] == b
