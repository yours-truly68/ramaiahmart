import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import SessionLocal
from app.main import app
from app.models.category import Category


@pytest.fixture
def test_category() -> Category:
    """Ensure a valid test category exists in the database."""
    session = SessionLocal()
    slug = f"conv_cat_{uuid.uuid4().hex[:6]}"
    cat = Category(name=f"Conv Cat {uuid.uuid4().hex[:6]}", slug=slug, is_active=True)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    session.close()
    return cat


async def create_user_and_token(
    client: AsyncClient, email_prefix: str
) -> tuple[str, str, uuid.UUID]:
    email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@msrit.edu"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "name": f"User {email_prefix.title()}",
            "accepted_terms": True,
            "accepted_privacy": True,
        },
    )
    assert reg_res.status_code == 201
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_id = uuid.UUID(me_res.json()["id"])
    return email, token, user_id


@pytest.mark.asyncio
async def test_conversation_lifecycle(test_category: Category) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create Seller (User A) and Buyer (User B) and Outsider (User C)
        _, token_a, user_id_a = await create_user_and_token(client, "seller")
        _, token_b, user_id_b = await create_user_and_token(client, "buyer")
        _, token_c, _ = await create_user_and_token(client, "outsider")

        # Seller creates and publishes a post
        post_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Calculus Textbook 9th Ed",
                "description": "Mint condition textbook for engineering calculus course.",
                "price": "450.00",
            },
        )
        assert post_res.status_code == 201
        post_id = post_res.json()["id"]

        # Publish post
        pub_res = await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "PUBLISHED"

        # 1. Seller cannot message own post
        self_res = await client.post(
            f"/api/v1/posts/{post_id}/conversations",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert self_res.status_code == 400
        assert self_res.json()["error"]["code"] == "CANNOT_MESSAGE_OWN_POST"

        # 2. Buyer creates conversation with Seller
        conv_res = await client.post(
            f"/api/v1/posts/{post_id}/conversations",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert conv_res.status_code == 200
        conv_data = conv_res.json()
        conv_id = conv_data["id"]
        assert conv_data["post_id"] == post_id
        assert conv_data["post_title"] == "Calculus Textbook 9th Ed"
        assert conv_data["other_participant"]["id"] == str(user_id_a)
        assert conv_data["unread_count"] == 0

        # 3. Duplicate conversation request returns existing conversation
        dup_res = await client.post(
            f"/api/v1/posts/{post_id}/conversations",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["id"] == conv_id

        # 4. Outsider cannot access conversation
        out_res = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token_c}"},
        )
        assert out_res.status_code == 403
        assert out_res.json()["error"]["code"] == "FORBIDDEN_NOT_PARTICIPANT"

        # 5. Buyer sends a message
        msg_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "Hi, is this textbook still available?"},
        )
        assert msg_res.status_code == 201
        msg_data = msg_res.json()
        assert msg_data["content"] == "Hi, is this textbook still available?"
        assert msg_data["sender_id"] == str(user_id_b)
        assert msg_data["read_at"] is None

        # 6. Message length validation
        blank_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "   "},
        )
        assert blank_res.status_code == 422

        toolong_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "A" * 2001},
        )
        assert toolong_res.status_code == 422

        # 7. Seller sees 1 unread message in conversation list
        list_res = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] == 1
        assert list_data["items"][0]["unread_count"] == 1
        assert list_data["items"][0]["other_participant"]["id"] == str(user_id_b)

        # 8. Seller reads messages -> marks as read
        read_res = await client.get(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert read_res.status_code == 200
        messages = read_res.json()
        assert len(messages) == 1
        assert messages[0]["read_at"] is not None

        # Seller's unread count is now 0
        list_res_after = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_res_after.json()["items"][0]["unread_count"] == 0

        # 9. Seller replies
        reply_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"content": "Yes it is! Can meet near ESB at 4pm."},
        )
        assert reply_res.status_code == 201

        # 10. Close conversation
        close_res = await client.post(
            f"/api/v1/conversations/{conv_id}/close",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert close_res.status_code == 200
        assert close_res.json()["closed_at"] is not None

        # 11. Cannot message closed conversation
        closed_msg_res = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"content": "Sounds good!"},
        )
        assert closed_msg_res.status_code == 400
        assert closed_msg_res.json()["error"]["code"] == "CONVERSATION_CLOSED"


@pytest.mark.asyncio
async def test_whatsapp_configuration_and_post_url(test_category: Category) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        _, token_a, _ = await create_user_and_token(client, "wa_seller")
        _, token_b, _ = await create_user_and_token(client, "wa_viewer")

        # 1. Initially WhatsApp is disabled
        me_res = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["whatsapp_enabled"] is False
        assert me_res.json()["whatsapp_number"] is None

        # 2. Cannot enable WhatsApp without a number
        err_res = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"whatsapp_enabled": True},
        )
        assert err_res.status_code == 400
        assert err_res.json()["error"]["code"] == "WHATSAPP_NUMBER_REQUIRED"

        # 3. Reject non-international number (no +)
        err_res2 = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"whatsapp_number": "9876543210"},
        )
        assert err_res2.status_code == 422

        # 4. Valid international number can be saved and enabled
        save_res = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"whatsapp_number": "+91 98765 43210", "whatsapp_enabled": True},
        )
        assert save_res.status_code == 200
        assert save_res.json()["whatsapp_enabled"] is True
        assert save_res.json()["whatsapp_number"] == "+919876543210"

        # 5. Create and publish a post
        post_res = await client.post(
            "/api/v1/posts",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "type": "OFFER",
                "category_id": str(test_category.id),
                "title": "Lab Coat Size L",
                "description": "Clean white lab coat for chemistry practicals.",
                "price": "200.00",
            },
        )
        assert post_res.status_code == 201
        post_id = post_res.json()["id"]

        pub_res = await client.post(
            f"/api/v1/posts/{post_id}/publish",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert pub_res.status_code == 200

        # 6. Viewing post detail yields wa.me link with prefilled text
        detail_res = await client.get(
            f"/api/v1/posts/{post_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert detail_res.status_code == 200
        post_data = detail_res.json()
        assert "whatsapp_url" in post_data
        assert post_data["whatsapp_url"] is not None
        assert "https://wa.me/919876543210" in post_data["whatsapp_url"]
        assert "Lab%20Coat%20Size%20L" in post_data["whatsapp_url"]
        # Public post does NOT expose raw whatsapp_number
        assert "whatsapp_number" not in post_data["author"]

        # 7. Disabling WhatsApp clears whatsapp_url on post
        await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"whatsapp_enabled": False},
        )
        detail_res_disabled = await client.get(
            f"/api/v1/posts/{post_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert detail_res_disabled.json()["whatsapp_url"] is None
