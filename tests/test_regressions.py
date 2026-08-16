import uuid
from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from backend.agent.tools import get_weather
from backend.main import app
from backend.services.recommendation_engine import build_top_outfits


client = TestClient(app)


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


def _register_and_login(username):
    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "password123",
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_invalid_login_rejected():
    username = _unique("invalid_login")
    _register_and_login(username)
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_invalid_token_rejected():
    response = client.get(
        "/profile/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_profile_duplicate_returns_409():
    username = _unique("duplicate_profile")
    headers = _register_and_login(username)
    payload = {
        "style": "休闲",
        "favorite_color": "白色",
        "body_type": "标准",
        "season": "夏季",
    }
    assert client.post("/profile/create", headers=headers, json=payload).status_code == 201
    assert client.post("/profile/create", headers=headers, json=payload).status_code == 409


def test_wardrobe_update_preserves_recognition_status_when_omitted():
    username = _unique("keep_status")
    headers = _register_and_login(username)
    created = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "recognition_status": "confirmed",
        },
    )
    assert created.status_code == 201
    clothes_id = created.json()["clothes_id"]

    updated = client.put(
        f"/wardrobe/{clothes_id}",
        headers=headers,
        json={
            "name": "白色长袖T恤",
            "category": "上衣",
            "color": "白色",
            "season": "春秋",
            "style": "休闲",
        },
    )
    assert updated.status_code == 200

    items = client.get("/wardrobe/", headers=headers).json()
    item = next(item for item in items if item["id"] == clothes_id)
    assert item["name"] == "白色长袖T恤"
    assert item["recognition_status"] == "confirmed"


def test_invalid_image_upload_returns_400():
    username = _unique("bad_image")
    headers = _register_and_login(username)
    response = client.post(
        "/wardrobe/analyze-image",
        headers=headers,
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400

    auto_response = client.post(
        "/wardrobe/upload-and-confirm",
        headers=headers,
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert auto_response.status_code == 400


def test_feedback_invalid_type_returns_422():
    username = _unique("bad_feedback")
    headers = _register_and_login(username)
    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "unknown",
            "outfit_score": 100,
            "outfit_snapshot": {},
            "reason": [],
        },
    )
    assert response.status_code == 422


def test_dislike_removes_color_from_favorite_colors():
    username = _unique("dislike_color")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色", "白色"],
            "avoid_colors": [],
        },
    )

    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"颜色": "蓝色"},
            "reason": ["不喜欢蓝色"],
        },
    )
    assert response.status_code == 201

    profile = client.get("/profile/me", headers=headers).json()
    assert "蓝色" in profile["avoid_colors"]
    assert "蓝色" not in profile["favorite_colors"]
    assert "白色" in profile["favorite_colors"]


def test_dislike_does_not_infer_color_from_item_name():
    username = _unique("no_color_guess")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )

    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"items": ["蓝色牛仔裤"]},
            "reason": ["版型不合适"],
        },
    )
    assert response.status_code == 201

    profile = client.get("/profile/me", headers=headers).json()
    assert profile["avoid_colors"] == []


def test_dislike_does_not_infer_color_from_generated_reason():
    username = _unique("no_generated_reason")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )

    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {},
            "reason": ["白色/灰色配色协调", "适合夏季", "用户喜欢休闲风格"],
        },
    )
    assert response.status_code == 201

    profile = client.get("/profile/me", headers=headers).json()
    assert profile["avoid_colors"] == []
    assert "白色" in profile["favorite_colors"]
    assert "灰色" in profile["favorite_colors"]
    assert "蓝色" in profile["favorite_colors"]


def test_clear_feedback_and_conversations():
    username = _unique("clear_feedback")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )
    client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"items": ["白色T恤"]},
            "reason": ["不喜欢这套"],
        },
    )
    assert len(client.get("/feedback/", headers=headers).json()) == 1

    feedback_reset = client.delete("/feedback/", headers=headers)
    assert feedback_reset.status_code == 200
    assert client.get("/feedback/", headers=headers).json() == []

    chat_reset = client.delete("/chat/conversations", headers=headers)
    assert chat_reset.status_code == 200
    assert client.get("/chat/conversations", headers=headers).json() == []


def test_agent_recommend_honors_avoid_black_from_query():
    username = _unique("avoid_black_query")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "黑色", "蓝色"],
            "avoid_colors": [],
        },
    )
    wardrobe_items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "color_tags": ["白色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "color_tags": ["灰色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "黑色西装",
            "category": "外套",
            "color": "黑色",
            "season": "夏季",
            "style": "商务",
            "color_tags": ["黑色"],
            "style_tags": ["商务"],
            "fit_tags": ["修身"],
            "occasion_tags": ["通勤"],
        },
    ]
    for item in wardrobe_items:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "不要推荐黑色，明天通勤怎么穿",
            "city": "沈阳",
            "occasion": "通勤",
        },
    )
    assert response.status_code == 200
    data = response.json()
    items = data["recommendation"]["items"]
    assert items
    assert all(item.get("color") != "黑色" for item in items)
    assert "本次避开黑色" in data["explanation"]
    assert "请取消" not in data["explanation"]


def test_interview_chat_does_not_recommend_sneakers():
    username = _unique("interview_no_sneakers")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常", "运动"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["婚礼", "宴会", "商务"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "我要去参加面试，要求穿得正式一点，怎么穿？"},
    )
    assert response.status_code == 200
    data = response.json()["reply"]
    item_names = [item["name"] for item in data["recommendation"]["items"]]
    assert not any("运动鞋" in name for name in item_names)
    assert "皮鞋" in data["explanation"]
    assert "面试场景" in data["explanation"]
    assert "核心穿搭完整" not in data["explanation"]
    assert data["recommendation"]["shoe_feedback"]["status"] == "missing"


def test_weekend_query_uses_weekend_label():
    username = _unique("weekend_label")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "周末去爬山，怎么穿？"},
    )
    assert response.status_code == 200
    explanation = response.json()["reply"]["explanation"]
    assert "周末沈阳" in explanation
    assert "今天沈阳" not in explanation


def test_request_avoid_color_does_not_change_long_term_memory():
    username = _unique("request_avoid")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色", "白色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户但不要蓝色，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert all(item.get("color") != "蓝色" for item in reply["recommendation"]["items"])
    assert "本次避开蓝色" in reply["explanation"]
    assert "请取消" not in reply["explanation"]

    profile = client.get("/profile/me", headers=headers).json()
    assert "蓝色" in profile["favorite_colors"]
    assert "蓝色" not in profile["avoid_colors"]
    assert "蓝色" in reply["memory"]["profile"]["favorite_colors"]


def test_casual_customer_request_respects_tshirt_and_excludes_shirt_suit():
    username = _unique("casual_tshirt")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["婚礼", "宴会", "商务"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={
            "message": "明天见客户，休闲一点，但我想穿T恤，不要衬衫和西装。"
        },
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert any("T恤" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("衬衣", "衬衫", "西装")
    )
    assert "缺少商务风格" not in reply["explanation"]


def test_casual_customer_request_does_not_recommend_suit_without_explicit_ban():
    username = _unique("casual_no_ban")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["婚礼", "宴会", "商务"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户，休闲一点，不要太正式，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply["scene"]["formality"] == 2
    assert reply["scene"]["style"] == "休闲"
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert not any("西装" in name for name in item_names)
    assert any("T恤" in name for name in item_names)


def test_formal_but_not_too_serious_does_not_force_suit():
    username = _unique("formal_relaxed")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色衬衫",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["商务会议"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户，正式一点但不要太严肃，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply["scene"]["formality"] == 3
    assert reply["scene"]["style"] == "商务"
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert not any("西装" in name for name in item_names)


def test_formal_but_not_too_serious_rejects_tshirt_jeans_sneakers():
    username = _unique("formal_no_suitable")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户，正式一点但不要太严肃，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply["scene"]["formality"] == 3
    assert reply["recommendation"]["items"] == []
    assert "缺少商务风格衣物" in reply["explanation"]


def test_customer_tshirt_request_overrides_shirt_and_suit():
    username = _unique("tshirt_formal")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户，我想穿T恤，但要正式一点。"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply["scene"]["formality"] == 3
    assert reply["scene"]["style"] == "商务"
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert any("T恤" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("衬衣", "衬衫", "西装")
    )


def test_tshirt_without_shirt_suit_keeps_sneakers():
    username = _unique("tshirt_no_shirt_suit")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天见客户，我想穿T恤，不要衬衫和西装。"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert any("T恤" in name for name in item_names)
    assert any("运动鞋" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("衬衣", "衬衫", "西装")
    )
    assert "缺少鞋子" not in reply["explanation"]


def test_fitness_recommendation_prefers_sport_tagged_items():
    username = _unique("fitness_sport_tags")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "速干运动T恤",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["速干"],
            "occasion_tags": ["运动"],
        },
        {
            "name": "灰色运动裤",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["运动"],
            "occasion_tags": ["运动"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色运动鞋",
            "category": "鞋子",
            "color": "灰色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["运动", "Fitness"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天去健身，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    item_names = [item["name"] for item in reply["recommendation"]["items"]]
    assert "速干运动T恤" in item_names
    assert "灰色运动鞋" in item_names
    assert "建议优先选择运动鞋" not in reply["explanation"]
    shoe_feedback = reply["recommendation"]["shoe_feedback"]
    assert shoe_feedback["status"] == "suitable"
    assert shoe_feedback["current_shoe"] == "灰色运动鞋"
    assert shoe_feedback["suitable"] is True
    assert "核心穿搭完整" in reply["recommendation"]["summary"]


def test_camping_sneaker_is_suitable_without_hiking_requirement():
    username = _unique("camping_sneaker_ok")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色速干T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["速干"],
            "occasion_tags": ["户外"],
        },
        {
            "name": "灰色速干裤",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": ["速干"],
            "occasion_tags": ["户外"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/chat/",
        headers=headers,
        json={"message": "周末去露营，怎么穿？"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    shoe_feedback = reply["recommendation"]["shoe_feedback"]
    assert shoe_feedback["status"] == "suitable"
    assert shoe_feedback["suitable"] is True
    assert "鞋子不满足当前场景要求" not in reply["explanation"]
    assert "防滑户外鞋" not in reply["explanation"]
    assert "核心穿搭完整" in reply["recommendation"]["summary"]


def test_disliked_outfit_is_not_recommended_first_again():
    username = _unique("dislike_outfit")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    first = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    assert first.status_code == 200
    first_items = first.json()["reply"]["recommendation"]["items"]
    first_names = {item["name"] for item in first_items}

    dislike = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"items": list(first_names)},
            "reason": ["不喜欢这套"],
        },
    )
    assert dislike.status_code == 201

    second = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    assert second.status_code == 200
    second_items = second.json()["reply"]["recommendation"]["items"]
    second_names = {item["name"] for item in second_items}
    assert second_names != first_names


def test_all_outfits_blocked_returns_friendly_message():
    username = _unique("all_disliked")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "运动",
            "fit_tags": ["基础款"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    first = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    first_names = {
        item["name"]
        for item in first.json()["reply"]["recommendation"]["items"]
    }
    client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"items": list(first_names)},
            "reason": ["不喜欢这套"],
        },
    )

    second = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    second_names = {
        item["name"]
        for item in second.json()["reply"]["recommendation"]["items"]
    }
    assert second_names != first_names
    client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"items": list(second_names)},
            "reason": ["不喜欢这套"],
        },
    )

    third = client.post(
        "/chat/",
        headers=headers,
        json={"message": "今天日常怎么穿？"},
    )
    third_reply = third.json()["reply"]
    assert third_reply["recommendation"]["items"] == []
    assert "补充新单品" in third_reply["explanation"]


def test_force_outerwear_overrides_summer_season_filter():
    profile = SimpleNamespace(season="夏季")
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色短裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 3,
            "name": "蓝色薄外套",
            "category": "外套",
            "color": "蓝色",
            "style": "休闲",
            "season": "夏季",
            "score": 80,
            "reason": ["风格"],
        },
    ]

    results = build_top_outfits(
        clothes,
        profile,
        force_slot=["外套"],
    )
    assert "外套" in results[0]["outfit"]


def test_wardrobe_ownership_errors():
    owner = _unique("owner_a")
    owner_headers = _register_and_login(owner)
    created = client.post(
        "/wardrobe/add",
        headers=owner_headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
        },
    )
    assert created.status_code == 201
    clothes_id = created.json()["clothes_id"]

    other_headers = _register_and_login(_unique("owner_b"))
    update_response = client.put(
        f"/wardrobe/{clothes_id}",
        headers=other_headers,
        json={
            "name": "黑色T恤",
            "category": "上衣",
            "color": "黑色",
            "season": "夏季",
            "style": "休闲",
        },
    )
    assert update_response.status_code == 403

    delete_response = client.delete(
        f"/wardrobe/{clothes_id}",
        headers=other_headers,
    )
    assert delete_response.status_code == 403
    assert client.get("/wardrobe/", headers=other_headers).json() == []


def test_chat_session_ownership_denied():
    owner_headers = _register_and_login(_unique("chat_owner"))
    session_id = _unique("session")
    created = client.post(
        "/chat/",
        headers=owner_headers,
        json={"session_id": session_id, "message": "你好"},
    )
    assert created.status_code == 200

    other_headers = _register_and_login(_unique("chat_other"))
    denied = client.post(
        "/chat/",
        headers=other_headers,
        json={"session_id": session_id, "message": "继续"},
    )
    assert denied.status_code == 403

    not_found = client.get(
        f"/chat/conversations/{session_id}",
        headers=other_headers,
    )
    assert not_found.status_code == 404


def test_recommend_without_matching_clothes_returns_friendly_message():
    username = _unique("no_match")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "avoid_colors": ["白色"],
        },
    )

    response = client.get("/recommend/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["items"] == []
    assert any("衣物" in item for item in data["recommendation"]["summary"])
    assert data["history_id"] is not None


def test_weather_api_failure_falls_back(monkeypatch):
    def raise_request_error(*args, **kwargs):
        raise RuntimeError("network offline")

    monkeypatch.setattr("backend.agent.tools.requests.get", raise_request_error)
    weather = get_weather("上海", use_api=True)
    assert weather["source"] == "fallback"
    assert weather["temperature"] == 28


def test_upload_analyze_and_confirm_ownership(monkeypatch):
    owner_headers = _register_and_login(_unique("task_owner"))
    image = BytesIO()
    Image.new("RGB", (32, 32), (255, 255, 255)).save(image, format="JPEG")
    image.seek(0)
    uploaded = client.post(
        "/wardrobe/analyze-image",
        headers=owner_headers,
        files={"file": ("white.jpg", image, "image/jpeg")},
    )
    assert uploaded.status_code == 200
    task_id = uploaded.json()["task_id"]

    other_headers = _register_and_login(_unique("task_other"))
    update_response = client.put(
        f"/wardrobe/task/{task_id}",
        headers=other_headers,
        json={"name": "修改后的衣物"},
    )
    assert update_response.status_code == 403

    confirm_response = client.post(
        f"/wardrobe/confirm-task/{task_id}",
        headers=other_headers,
    )
    assert confirm_response.status_code == 403


def test_agent_hard_requires_shirt_and_pants_for_casual_query():
    username = _unique("required_casual")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色衬衫",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天日常穿衬衫和裤子，怎么搭？",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert any("裤子" in name for name in item_names)
    assert not any("T恤" in name for name in item_names)


def test_agent_keeps_shirt_pants_and_excludes_suit_for_interview():
    username = _unique("interview_shirt_pants")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "商务",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["直筒"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "明天面试，只推荐衬衫和裤子，不要西装",
            "city": "沈阳",
            "occasion": "面试",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert any("裤子" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("西装", "西服", "T恤")
    )


def test_agent_only_recommend_shirt_pants_does_not_add_suit_or_shoes():
    username = _unique("only_shirt_pants")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "商务",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["直筒"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "明天面试，只推荐衬衫和裤子",
            "city": "沈阳",
            "occasion": "面试",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert any("裤子" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("西装", "西服", "运动鞋")
    )


def test_agent_only_recommend_shirt_without_pants():
    username = _unique("only_shirt_no_pants")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "不要裤子，只推荐衬衫",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert not any("裤子" in name for name in item_names)
    assert not any(
        "裤子" in summary
        for summary in response.json()["recommendation"]["summary"]
    )


def test_agent_only_recommend_shirt_and_shoes_without_pants():
    username = _unique("only_shirt_shoes")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "不要裤子，只推荐衬衫和鞋子",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert any("运动鞋" in name for name in item_names)
    assert not any("裤子" in name for name in item_names)


def test_agent_only_xiku_does_not_fall_back_to_jeans():
    username = _unique("only_xiku")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "商务",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["商务"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐西裤和衬衫",
            "city": "沈阳",
            "occasion": "商务",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("缺少西裤" in summary for summary in data["summary"])


def test_agent_only_recommend_white_does_not_add_other_colors():
    username = _unique("only_white")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色裤子",
            "category": "裤子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐白色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("白色" in name for name in item_names)
    assert not any("灰色" in name for name in item_names)


def test_chat_only_color_does_not_bleed_to_next_request():
    username = _unique("chat_only_color")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    first = client.post(
        "/chat/",
        headers=headers,
        json={"message": "只推荐蓝色"},
    )
    assert first.status_code == 200
    session_id = first.json()["session_id"]

    second = client.post(
        "/chat/",
        headers=headers,
        json={
            "session_id": session_id,
            "message": "不要蓝色，只推荐白色",
        },
    )
    assert second.status_code == 200
    second_names = [
        item["name"]
        for item in second.json()["reply"]["recommendation"]["items"]
    ]
    assert any("白色" in name for name in second_names)
    assert not any(
        keyword in name
        for name in second_names
        for keyword in ("蓝色", "灰色")
    )
    profile = client.get("/profile/me", headers=headers).json()
    assert "蓝色" not in profile["avoid_colors"]

    third = client.post(
        "/chat/",
        headers=headers,
        json={
            "session_id": session_id,
            "message": "只推荐白色",
        },
    )
    assert third.status_code == 200
    third_names = [
        item["name"]
        for item in third.json()["reply"]["recommendation"]["items"]
    ]
    assert any("白色" in name for name in third_names)
    assert not any("蓝色" in name for name in third_names)


def test_agent_only_recommend_top_does_not_add_pants_or_shoes():
    username = _unique("only_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐上衣",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("裤子", "运动鞋")
    )


def test_agent_daily_with_sport_style_keeps_daily_scene():
    username = _unique("daily_sport_style")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天日常穿，要运动风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    scene = response.json()["scene"]
    assert scene["scene_type"] == "日常"
    assert scene["style"] == "运动"


def test_agent_sport_style_only_top_does_not_recommend_casual_shirt():
    username = _unique("sport_only_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，要运动风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    scene = response.json()["scene"]
    assert scene["scene_type"] == "日常"
    assert scene["style"] == "运动"
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []
    assert not any("衬衫" in name for name in item_names)
    assert any(
        "符合运动风格" in summary
        for summary in data["summary"]
    )


def test_agent_only_sport_style_top_recommends_sport_jacket():
    username = _unique("sport_jacket")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "绿色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["绿色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["运动"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "高领拉链运动夹克",
            "category": "上衣",
            "color": "绿色",
            "season": "四季",
            "style": "运动",
            "fit_tags": ["修身"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐运动风上衣",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("运动夹克" in name for name in item_names)
    assert not any("灰色衬衫" in name for name in item_names)


def test_agent_contradictory_sport_style_returns_conflict():
    username = _unique("sport_style_conflict")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "绿色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["绿色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "高领拉链运动夹克",
            "category": "上衣",
            "color": "绿色",
            "season": "四季",
            "style": "运动",
            "fit_tags": ["修身"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐运动风上衣，不要运动风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("冲突" in summary for summary in data["summary"])


def test_agent_only_long_sleeve_shirt_does_not_use_short_sleeve():
    username = _unique("long_sleeve_shirt")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐长袖衬衫",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("长袖" in name for name in item_names)
    assert not any(name == "灰色衬衫" for name in item_names)
    assert not any(name == "蓝色衬衫" for name in item_names)


def test_agent_gray_top_no_long_sleeve_recommends_gray_shirt():
    username = _unique("gray_no_long_sleeve")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐灰色上衣，不要长袖",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("灰色衬衫" in name for name in item_names)


def test_agent_no_sport_style_recommends_casual_top():
    username = _unique("no_sport_style")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐上衣，不要运动风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("灰色衬衫" in name for name in item_names)
    assert not any("冲突" in summary for summary in response.json()["recommendation"]["summary"])


def test_chat_business_style_does_not_leak_to_next_request():
    username = _unique("style_no_leak")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    first = client.post(
        "/chat/",
        headers=headers,
        json={"message": "要商务风"},
    )
    assert first.status_code == 200
    session_id = first.json()["session_id"]

    second = client.post(
        "/chat/",
        headers=headers,
        json={
            "session_id": session_id,
            "message": "今天日常穿，只推荐蓝色衣服",
        },
    )
    assert second.status_code == 200
    explanation = second.json()["reply"]["explanation"]
    assert "本次要求：商务风格" not in explanation


def test_agent_fitness_scene_only_top_does_not_recommend_casual_tshirt():
    username = _unique("fitness_only_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天去健身，只推荐上衣，不要黑色",
            "city": "沈阳",
            "occasion": "健身",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []
    assert not any("T恤" in name for name in item_names)


def test_agent_required_blue_color_filters_gray_top():
    username = _unique("required_blue_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，不要黑色，要蓝色，休闲风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("蓝色衬衫" in name for name in item_names)
    assert not any("灰色衬衫" in name for name in item_names)


def test_agent_outdoor_only_top_does_not_recommend_casual_shirt():
    username = _unique("outdoor_only_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "去户外/露营，只推荐上衣",
            "city": "沈阳",
            "occasion": "露营",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []
    assert not any("衬衫" in name for name in item_names)
    assert any(
        "露营" in summary or "户外" in summary
        for summary in data["summary"]
    )
    assert not any(
        "缺少休闲风格衣物" in summary
        for summary in data["summary"]
    )


def test_agent_contradictory_color_returns_conflict_message():
    username = _unique("color_conflict")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，要蓝色，不要蓝色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("冲突" in summary for summary in data["summary"])


def test_agent_missing_required_color_reports_color_in_message():
    username = _unique("missing_purple_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，要紫色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("紫色上衣" in summary for summary in data["summary"])


def test_agent_contradictory_item_returns_conflict_message():
    username = _unique("item_conflict")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，不要上衣",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("冲突" in summary for summary in data["summary"])


def test_agent_contradictory_style_returns_conflict_message():
    username = _unique("style_conflict")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，要休闲风，不要休闲风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    assert data["items"] == []
    assert any("冲突" in summary for summary in data["summary"])


def test_agent_formal_style_does_not_accept_casual_shirt_with_formal_tags():
    username = _unique("formal_tag_casual_shirt")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "我只要上衣，要正式风格，不要黑色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []
    assert not any("衬衣" in name or "衬衫" in name for name in item_names)


def test_agent_client_formal_recommends_tagged_casual_shirt():
    username = _unique("client_formal_tag_shirt")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "修身",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["婚礼", "宴会", "商务"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "明天见客户，正式一点",
            "city": "沈阳",
            "occasion": "客户",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("长袖" in name for name in item_names)


def test_agent_interview_query_keeps_interview_scene_label():
    username = _unique("interview_scene_label")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "商务",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["面试", "商务"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["直筒"],
            "occasion_tags": ["面试", "商务"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "面试，只推荐衬衫和裤子，不要黑色",
            "city": "沈阳",
            "occasion": "面试",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scene"]["scene_type"] == "面试"
    assert "面试场景" in data["explanation"]


def test_agent_wedding_formal_style_does_not_recommend_casual_shirt():
    username = _unique("wedding_formal_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["婚礼"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "周末参加婚礼，只推荐上衣，要正式风格",
            "city": "沈阳",
            "occasion": "婚礼",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []


def test_agent_business_style_only_top_does_not_require_pants():
    username = _unique("business_only_top")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["商务"],
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天日常穿，要商务风，只推荐上衣",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert any("衬衫" in name for name in item_names)
    assert not any(
        keyword in name
        for name in item_names
        for keyword in ("裤子", "运动鞋")
    )


def test_agent_business_style_only_shoes_does_not_fallback_to_sneakers():
    username = _unique("business_only_shoes")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "season": "夏季",
            "style": "运动",
            "fit_tags": [],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天日常穿，要商务风，只推荐鞋子，不要黑色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    data = response.json()["recommendation"]
    item_names = [item["name"] for item in data["items"]]
    assert item_names == []
    assert not any("运动鞋" in name for name in item_names)
    assert any("缺少" in summary for summary in data["summary"])


def test_agent_business_style_filters_casual_items():
    username = _unique("business_hard")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "灰色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["商务"],
        },
    ]:
        response = client.post("/wardrobe/add", headers=headers, json=item)
        assert response.status_code == 201

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "要商务风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert response.status_code == 200
    item_names = [
        item["name"]
        for item in response.json()["recommendation"]["items"]
    ]
    assert not any("灰色衬衫" in name for name in item_names)
    assert not any("灰色裤子" in name for name in item_names)
