import uuid

import pytest


@pytest.mark.asyncio
async def test_login_ok(client):
    res = await client.post(
        "/api/auth/token",
        data={"username": "tester@dupla.demo", "password": "testpass123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body


@pytest.mark.asyncio
async def test_login_fail(client):
    res = await client.post(
        "/api/auth/token",
        data={"username": "tester@dupla.demo", "password": "wrong"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    res = await client.get("/api/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_ok(client, auth_headers_async: dict[str, str]):
    res = await client.get("/api/me", headers=auth_headers_async)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "tester@dupla.demo"


@pytest.mark.asyncio
async def test_modules_cached_flow(client, auth_headers_async: dict[str, str]):
    a = await client.get("/api/modules", headers=auth_headers_async)
    b = await client.get("/api/modules", headers=auth_headers_async)
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json() == b.json()


@pytest.mark.asyncio
async def test_coordinator_cannot_create_project(client, auth_headers_async: dict[str, str]):
    res = await client.post(
        "/api/projects",
        headers={**auth_headers_async, "Content-Type": "application/json"},
        json={"name": "No debe existir", "client_name": None},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_project_architecture_flow(client, master_auth_headers_async: dict[str, str]):
    create = await client.post(
        "/api/projects",
        headers={**master_auth_headers_async, "Content-Type": "application/json"},
        json={"name": "Obra demo", "client_name": "Cliente"},
    )
    assert create.status_code == 201, create.text
    created = create.json()
    assert created["workflow_phase"] == "BOOTSTRAPPING"
    pid = created["uuid"]
    project_uuid = uuid.UUID(pid)

    get_empty = await client.get(
        f"/api/projects/{project_uuid}/architecture",
        headers=master_auth_headers_async,
    )
    assert get_empty.status_code == 200
    assert get_empty.json()["document"]["groups"] == []

    payload = {
        "groups": [
            {
                "id": str(uuid.uuid4()),
                "kind": "fase",
                "title": "Fase 1",
                "order": 0,
                "items": [
                    {
                        "id": str(uuid.uuid4()),
                        "descripcion": "Partida demo",
                        "unidad": "m2",
                        "cantidad": 10,
                        "precio_unitario": 5,
                        "subtotal": 50,
                    }
                ],
            }
        ],
        "materiales": [],
    }

    put = await client.put(
        f"/api/projects/{project_uuid}/architecture",
        headers={**master_auth_headers_async, "Content-Type": "application/json"},
        json=payload,
    )
    assert put.status_code == 204, put.text

    get_full = await client.get(
        f"/api/projects/{project_uuid}/architecture",
        headers=master_auth_headers_async,
    )
    assert get_full.status_code == 200
    assert len(get_full.json()["document"]["groups"]) == 1


@pytest.mark.asyncio
async def test_exports_return_bytes(client, master_auth_headers_async: dict[str, str]):
    create = await client.post(
        "/api/projects",
        headers={**master_auth_headers_async, "Content-Type": "application/json"},
        json={"name": "Export demo", "client_name": None},
    )
    assert create.status_code == 201
    assert create.json()["workflow_phase"] == "BOOTSTRAPPING"
    pid = uuid.UUID(create.json()["uuid"])

    xlsx = await client.get(f"/api/projects/{pid}/exports/pliego.xlsx", headers=master_auth_headers_async)
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"

    pdf = await client.get(f"/api/projects/{pid}/exports/pliego.pdf", headers=master_auth_headers_async)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
