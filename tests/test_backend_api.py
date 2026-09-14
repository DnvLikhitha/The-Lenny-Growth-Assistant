import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_app_db

@pytest.fixture(autouse=True)
def setup_db():
    init_app_db()

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["data"]["status"] == "ok"

def test_config_endpoint():
    response = client.get("/config")
    assert response.status_code == 200
    json_data = response.json()
    assert "active_provider" in json_data["data"]
    assert "active_model" in json_data["data"]

def test_session_crud():
    # 1. Create Session
    res = client.post("/sessions", json={"title": "Test Session"})
    assert res.status_code == 200
    sess = res.json()["data"]
    sess_id = sess["id"]
    assert sess["title"] == "Test Session"

    # 2. Get Session
    res_get = client.get(f"/sessions/{sess_id}")
    assert res_get.status_code == 200
    assert res_get.json()["data"]["id"] == sess_id

    # 3. List Sessions
    res_list = client.get("/sessions")
    assert res_list.status_code == 200
    ids = [s["id"] for s in res_list.json()["data"]]
    assert sess_id in ids

    # 4. Delete Session
    res_del = client.delete(f"/sessions/{sess_id}")
    assert res_del.status_code == 200
    assert res_del.json()["data"]["deleted"] is True

    # 5. Verify 404
    res_get_404 = client.get(f"/sessions/{sess_id}")
    assert res_get_404.status_code == 404
