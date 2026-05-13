"""
Test-Flow: User erstellen → Einloggen → Post erstellen → Post abrufen
Zeigt das Grundmuster für alle zukünftigen Tests.
"""


# ============================================================
# TEST 1: User erstellen (Happy Path)
# ============================================================
def test_create_user(client):
    response = client.post("/users/", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "geheim123"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password" not in data  # Passwort darf NIEMALS zurückkommen!
    assert "id" in data


# ============================================================
# TEST 2: User mit doppelter Email (Fehlerfall)
# ============================================================
def test_create_user_duplicate_email(client):
    # Erster User — funktioniert
    client.post("/users/", json={
        "username": "user1",
        "email": "same@example.com",
        "password": "geheim123"
    })

    # Zweiter User mit gleicher Email — muss fehlschlagen
    response = client.post("/users/", json={
        "username": "user2",
        "email": "same@example.com",
        "password": "geheim123"
    })

    assert response.status_code != 201  # Darf NICHT erfolgreich sein


# ============================================================
# TEST 3: Login (Happy Path)
# ============================================================
def test_login(client):
    # Erst User erstellen
    client.post("/users/", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "geheim123"
    })

    # Dann einloggen (OAuth2 erwartet form-data, nicht JSON)
    response = client.post("/login/", data={
        "username": "login@example.com",
        "password": "geheim123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ============================================================
# TEST 4: Login mit falschem Passwort (Fehlerfall)
# ============================================================
def test_login_wrong_password(client):
    # User erstellen
    client.post("/users/", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "geheim123"
    })

    # Mit falschem Passwort einloggen
    response = client.post("/login/", data={
        "username": "login@example.com",
        "password": "falsch"
    })

    assert response.status_code == 401


# ============================================================
# TEST 5: Post erstellen OHNE Login (Fehlerfall)
# ============================================================
def test_create_post_unauthorized(client):
    response = client.post("/posts/", json={
        "title": "Test Post",
        "content": "Inhalt"
    })

    assert response.status_code == 401  # Kein Token → kein Zugang


# ============================================================
# TEST 6: Post erstellen MIT Login (Happy Path)
# ============================================================
def test_create_post(client):
    # 1. User erstellen
    client.post("/users/", json={
        "username": "poster",
        "email": "poster@example.com",
        "password": "geheim123"
    })

    # 2. Einloggen → Token bekommen
    login_response = client.post("/login/", data={
        "username": "poster@example.com",
        "password": "geheim123"
    })
    token = login_response.json()["access_token"]

    # 3. Post erstellen mit Token im Header
    response = client.post(
        "/posts/",
        json={"title": "Mein Post", "content": "Hallo Welt"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Mein Post"
    assert data["content"] == "Hallo Welt"
    assert data["owner"]["username"] == "poster"


# ============================================================
# TEST 7: Posts abrufen
# ============================================================
def test_get_posts(client):
    # User + Login + Post erstellen (Setup)
    client.post("/users/", json={
        "username": "reader",
        "email": "reader@example.com",
        "password": "geheim123"
    })
    login_response = client.post("/login/", data={
        "username": "reader@example.com",
        "password": "geheim123"
    })
    token = login_response.json()["access_token"]
    client.post(
        "/posts/",
        json={"title": "Post 1", "content": "Inhalt 1"},
        headers={"Authorization": f"Bearer {token}"}
    )

    # GET /posts — braucht keinen Login
    response = client.get("/posts/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Post 1"
