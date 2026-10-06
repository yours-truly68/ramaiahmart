import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_user
from app.core.errors import AppException
from app.core.limiter import rate_limiter
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.post import Post, PostStatus, PostType
from app.models.user import User
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationPostSummary,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
    ParticipantSummary,
)
from app.services.lifecycle import record_user_activity

router = APIRouter(tags=["Conversations"])


def _build_conversation_response(
    conv: Conversation,
    current_user_id: uuid.UUID,
) -> ConversationResponse:
    other_user = conv.owner if current_user_id == conv.initiator_id else conv.initiator

    img_url = None
    if conv.post and conv.post.images:
        sorted_images = sorted(conv.post.images, key=lambda img: img.position)
        if sorted_images:
            first_img = sorted_images[0]
            if first_img.public_url:
                img_url = first_img.public_url
            elif first_img.storage_key:
                from app.services.storage import storage_service

                img_url = storage_service.generate_download_url(first_img.storage_key)

    unread_count = 0
    if conv.messages:
        unread_count = sum(
            1 for m in conv.messages if m.sender_id != current_user_id and m.read_at is None
        )

    post_summary = None
    if conv.post:
        post_summary = ConversationPostSummary(
            id=conv.post.id,
            title=conv.post.title,
            type=conv.post.type,
            status=conv.post.status,
            price=conv.post.price,
            price_unit=conv.post.price_unit,
            thumbnail_url=img_url,
        )

    return ConversationResponse(
        id=conv.id,
        post_id=conv.post_id,
        post_title=conv.post.title if conv.post else "Post",
        post_type=conv.post.type if conv.post else PostType.OFFER,
        post_image_url=img_url,
        post=post_summary,
        other_participant=ParticipantSummary(
            id=other_user.id,
            name=other_user.name,
            university_verified=other_user.university_verified,
            profile_image_key=other_user.profile_image_key,
        ),
        last_message_at=conv.last_message_at,
        closed_at=conv.closed_at,
        unread_count=unread_count,
        created_at=conv.created_at,
    )


def _load_conversation_by_id(
    conversation_id: uuid.UUID,
    db: Session,
) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .options(
            joinedload(Conversation.post).joinedload(Post.author),
            joinedload(Conversation.post).selectinload(Post.images),
            joinedload(Conversation.initiator),
            joinedload(Conversation.owner),
            selectinload(Conversation.messages),
        )
        .where(Conversation.id == conversation_id)
    )


@router.post(
    "/posts/{post_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Start or retrieve a conversation for a listing",
)
def create_or_get_conversation(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Start a new direct conversation about a post, or return existing one."""
    post = db.scalar(
        select(Post)
        .options(
            joinedload(Post.author),
            selectinload(Post.images),
        )
        .where(Post.id == post_id)
    )
    if post is None:
        raise AppException(
            code="POST_NOT_FOUND",
            message="Post not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if post.author_id == current_user.id:
        raise AppException(
            code="CANNOT_MESSAGE_OWN_POST",
            message="You cannot start a conversation on your own listing.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if post.status != PostStatus.PUBLISHED:
        raise AppException(
            code="POST_NOT_PUBLISHED",
            message="Conversations can only be started for published posts.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Check for existing conversation (post_id + initiator_id)
    existing = db.scalar(
        select(Conversation)
        .options(
            joinedload(Conversation.post).joinedload(Post.author),
            joinedload(Conversation.post).selectinload(Post.images),
            joinedload(Conversation.initiator),
            joinedload(Conversation.owner),
            selectinload(Conversation.messages),
        )
        .where(
            Conversation.post_id == post.id,
            Conversation.initiator_id == current_user.id,
        )
    )
    if existing is not None:
        return _build_conversation_response(existing, current_user.id)

    # Rate limiting: max 30 new conversations per hour per user
    allowed, retry_after = rate_limiter.storage.check_and_record(
        key=f"conv_create:user:{current_user.id}",
        limit=30,
        window_seconds=3600,
    )
    if not allowed:
        raise AppException(
            code="RATE_LIMITED",
            message="Too many conversation requests. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
        )

    new_conversation = Conversation(
        post_id=post.id,
        initiator_id=current_user.id,
        owner_id=post.author_id,
    )
    db.add(new_conversation)
    record_user_activity(current_user, db, commit=False)
    try:
        db.commit()
        db.refresh(new_conversation)
        conv_to_return = new_conversation
    except IntegrityError:
        db.rollback()
        # Fetch the existing conversation that won the concurrent creation race
        existing = db.scalar(
            select(Conversation).where(
                Conversation.post_id == post.id,
                Conversation.initiator_id == current_user.id,
            )
        )
        if existing is None:
            raise
        conv_to_return = existing

    loaded = _load_conversation_by_id(conv_to_return.id, db)
    assert loaded is not None
    return _build_conversation_response(loaded, current_user.id)


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List all conversations for authenticated user",
)
def list_conversations(
    limit: int = Query(default=50, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(default=0, ge=0, description="Number of conversations to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """Retrieve conversations where the user is initiator or owner with pagination."""
    filter_cond = or_(
        Conversation.initiator_id == current_user.id,
        Conversation.owner_id == current_user.id,
    )
    total_count = db.scalar(select(func.count(Conversation.id)).where(filter_cond)) or 0

    rows = db.scalars(
        select(Conversation)
        .options(
            joinedload(Conversation.post).joinedload(Post.author),
            joinedload(Conversation.post).selectinload(Post.images),
            joinedload(Conversation.initiator),
            joinedload(Conversation.owner),
            selectinload(Conversation.messages),
        )
        .where(filter_cond)
        .order_by(
            func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
            Conversation.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    items = [_build_conversation_response(c, current_user.id) for c in rows]
    unread_total = sum(item.unread_count for item in items)

    return ConversationListResponse(
        items=items,
        total=total_count,
        unread_total=unread_total,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Retrieve details for a specific conversation."""
    conversation = _load_conversation_by_id(conversation_id, db)
    if conversation is None:
        raise AppException(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user.id not in (conversation.initiator_id, conversation.owner_id):
        raise AppException(
            code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not a participant in this conversation.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return _build_conversation_response(conversation, current_user.id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="List messages in a conversation and mark as read",
)
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=200, description="Max messages to return"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    """Retrieve chronological messages in conversation and mark incoming messages as read."""
    conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if conversation is None:
        raise AppException(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user.id not in (conversation.initiator_id, conversation.owner_id):
        raise AppException(
            code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not a participant in this conversation.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Mark all unread messages sent by the OTHER participant as read
    now = datetime.now(UTC)
    db.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.sender_id != current_user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=now)
    )
    record_user_activity(current_user, db, commit=False)
    db.commit()

    # Fetch ordered messages with pagination
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message in a conversation",
)
def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send a new message to a conversation."""
    conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if conversation is None:
        raise AppException(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user.id not in (conversation.initiator_id, conversation.owner_id):
        raise AppException(
            code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not a participant in this conversation.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if conversation.closed_at is not None:
        raise AppException(
            code="CONVERSATION_CLOSED",
            message="Cannot send messages to a closed conversation.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Rate limiting: max 60 messages per minute per user
    allowed, retry_after = rate_limiter.storage.check_and_record(
        key=f"msg_send:user:{current_user.id}",
        limit=60,
        window_seconds=60,
    )
    if not allowed:
        raise AppException(
            code="RATE_LIMITED",
            message="Message sending rate limit exceeded. Please wait a moment.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
        )

    now = datetime.now(UTC)
    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=data.content,
        created_at=now,
    )
    conversation.last_message_at = now
    db.add(message)
    record_user_activity(current_user, db, commit=False)
    db.commit()
    db.refresh(message)

    return MessageResponse.model_validate(message)


@router.post(
    "/conversations/{conversation_id}/close",
    response_model=ConversationResponse,
    summary="Close a conversation",
)
def close_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Close an active conversation. Participants only."""
    conversation = _load_conversation_by_id(conversation_id, db)
    if conversation is None:
        raise AppException(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user.id not in (conversation.initiator_id, conversation.owner_id):
        raise AppException(
            code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not a participant in this conversation.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if conversation.closed_at is None:
        conversation.closed_at = datetime.now(UTC)
        record_user_activity(current_user, db, commit=False)
        db.commit()
        db.refresh(conversation)

    return _build_conversation_response(conversation, current_user.id)
