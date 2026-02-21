"""Smoke test -- verify all endpoints work."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json

base = "http://127.0.0.1:5000"
s = requests.Session()

# 1. Login page
r = s.get(f"{base}/login")
assert r.status_code == 200, f"Login page failed: {r.status_code}"
assert "login-form" in r.text
print("[OK] GET /login -- 200")

# 2. Register
r = s.post(f"{base}/auth/register", json={"username": "smoketest", "email": "smoke@test.com", "password": "test123"})
print(f"[OK] POST /auth/register -- {r.status_code}: {r.json().get('message', r.json().get('error'))}")

# 3. Auth me
r = s.get(f"{base}/auth/me")
assert r.status_code == 200
data = r.json()
print(f"[OK] GET /auth/me -- user={data['user']['username']}, quota={data['quota']}")

# 4. Pages
for page in ["/notebook", "/upload", "/quiz", "/chat", "/profile", "/review"]:
    r = s.get(f"{base}{page}")
    assert r.status_code == 200, f"{page} returned {r.status_code}"
    print(f"[OK] GET {page} -- 200")

# 5. API endpoints
r = s.get(f"{base}/api/notes")
assert r.status_code == 200
print(f"[OK] GET /api/notes -- {r.json()['total']} notes")

r = s.get(f"{base}/api/subjects")
assert r.status_code == 200
print(f"[OK] GET /api/subjects -- {len(r.json()['subjects'])} subjects")

r = s.get(f"{base}/api/tags")
assert r.status_code == 200
print(f"[OK] GET /api/tags -- {len(r.json()['tags'])} tags")

r = s.get(f"{base}/api/models/vision")
assert r.status_code == 200
models = r.json()["models"]
print(f"[OK] GET /api/models/vision -- {len(models)} models: {[m['name'] for m in models]}")

r = s.get(f"{base}/api/models/chat")
assert r.status_code == 200
models = r.json()["models"]
print(f"[OK] GET /api/models/chat -- {len(models)} models")

r = s.get(f"{base}/api/chat/threads")
assert r.status_code == 200
print(f"[OK] GET /api/chat/threads -- {len(r.json()['threads'])} threads")

r = s.get(f"{base}/api/quiz/sessions")
assert r.status_code == 200
print(f"[OK] GET /api/quiz/sessions -- {len(r.json()['sessions'])} sessions")

# 6. Create a note
r = s.post(f"{base}/api/notes", json={
    "title": "Test Note",
    "subject": "Math",
    "tags": ["algebra", "equations"],
    "content_md": "## Test\n\nThis is a test note.",
    "status": "UNSOLVED",
    "mistake_items": [{
        "ocr_question": "Solve x^2 + 2x + 1 = 0",
        "ocr_answer": "x = -1",
        "status": "SOLVED",
        "confidence": 0.9,
    }]
})
assert r.status_code == 201
note = r.json()
print(f"[OK] POST /api/notes -- created note #{note['id']} with {len(note['mistake_items'])} items")

# 7. Get note
r = s.get(f"{base}/api/notes/{note['id']}")
assert r.status_code == 200
print(f"[OK] GET /api/notes/{note['id']} -- title={r.json()['title']}")

# 8. Update note
r = s.put(f"{base}/api/notes/{note['id']}", json={"title": "Updated Test Note", "status": "SOLVED"})
assert r.status_code == 200
print(f"[OK] PUT /api/notes/{note['id']} -- title={r.json()['title']}, status={r.json()['status']}")

# 9. Create chat thread
r = s.post(f"{base}/api/chat/threads", json={"title": "Test Thread"})
assert r.status_code == 201
thread = r.json()
print(f"[OK] POST /api/chat/threads -- created thread #{thread['id']}")

# 10. API key update
r = s.put(f"{base}/auth/api-key", json={"api_key": ""})
assert r.status_code == 200
print(f"[OK] PUT /auth/api-key -- {r.json()['message']}")

# 11. Logout & admin login
s.post(f"{base}/auth/logout")
r = s.post(f"{base}/auth/login", json={"username": "admin", "password": "admin123"})
assert r.status_code == 200
print(f"[OK] Admin login -- {r.json()['message']}")

# 12. Admin panel
r = s.get(f"{base}/admin/users")
assert r.status_code == 200
users = r.json()["users"]
print(f"[OK] GET /admin/users -- {len(users)} users")
for u in users:
    q = u.get("quota") or {}
    print(f"   - {u['username']} (admin={u['is_admin']}, chat={q.get('remaining_chat')}, img={q.get('remaining_images')}, quiz={q.get('remaining_quizzes')})")

# 13. Update quota
uid = [u for u in users if u["username"] == "smoketest"][0]["id"]
r = s.put(f"{base}/admin/users/{uid}/quota", json={"max_chat": 100, "remaining_chat": 100})
assert r.status_code == 200
print(f"[OK] PUT /admin/users/{uid}/quota -- {r.json()['message']}")

print("\n=== ALL SMOKE TESTS PASSED ===")
