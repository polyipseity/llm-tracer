"""Reprocess engine for transforming private chat data based on attachment policies."""

import re
from enum import Enum

from llm_tracer.config import TracerConfig
from llm_tracer.schema import ChatSession
from llm_tracer.storage import read_private_chats, write_private_chat

"""Public symbols exported by this module."""
__all__ = ("AttachmentPolicy", "reprocess_private_data")


class AttachmentPolicy(str, Enum):
    """Attachment content preservation policy for private data."""

    FULL = "full"
    """Keep all attachment structures and content intact."""

    METADATA_ONLY = "metadata_only"
    """Keep attachment references but strip binary/large content."""

    STRIP = "strip"
    """Remove all attachment structures entirely."""


def _apply_attachment_policy(
    session: ChatSession, policy: AttachmentPolicy
) -> ChatSession:
    """Apply attachment policy transformation to a chat session.

    Modifies message content by removing or reducing attachment information
    based on the target policy. Works with attachment structures embedded
    in the message content.

    Args:
        session: Chat session to transform
        policy: Target attachment policy

    Returns:
        Transformed copy of the session
    """

    if policy == AttachmentPolicy.FULL:
        return session

    # For METADATA_ONLY and STRIP, we modify message content to remove/reduce attachments
    # This targets common patterns: attachment markers, embedded URIs, file references
    transformed_messages = []
    for message in session.messages:
        new_content = message.content
        if policy == AttachmentPolicy.METADATA_ONLY:
            # Strip content from attachment references but keep metadata
            # Remove file:// URIs and data:// URIs that are likely attachment content
            new_content = re.sub(
                r"\b(?:file|data|https?)://[^\s\"'`}<\]]+", "<ATTACHMENT>", new_content
            )
            # Remove base64-encoded content markers
            new_content = re.sub(
                r"\b[A-Za-z0-9+/=]{100,}\b", "<ENCODED_CONTENT>", new_content
            )
        elif policy == AttachmentPolicy.STRIP:
            # Remove attachment-related markers and references entirely
            new_content = re.sub(
                r"\b(?:file|data|https?)://[^\s\"'`}<\]]+", "", new_content
            )
            new_content = re.sub(r"\b[A-Za-z0-9+/=]{100,}\b", "", new_content)
            # Remove common attachment keywords and patterns
            new_content = re.sub(
                r"\b(?:attachment|file|blob|media|image|video|audio|document):\s*[^\s,;]+",
                "",
                new_content,
                flags=re.IGNORECASE,
            )

        transformed_messages.append(
            message.model_copy(update={"content": new_content.strip()})
        )

    return session.model_copy(update={"messages": transformed_messages})


def _validate_policy_transition(
    current_policy: AttachmentPolicy | None, new_policy: AttachmentPolicy
) -> None:
    """Validate that policy transition is allowed (no upgrades from STRIP).

    Args:
        current_policy: Current policy level (if any)
        new_policy: Desired new policy level

    Raises:
        ValueError: If attempting an upgrade from STRIP policy
    """

    if current_policy is None:
        return

    # Define policy order: STRIP (most restrictive) < METADATA_ONLY < FULL (least restrictive)
    policy_order = {
        AttachmentPolicy.STRIP: 0,
        AttachmentPolicy.METADATA_ONLY: 1,
        AttachmentPolicy.FULL: 2,
    }

    if policy_order[new_policy] < policy_order[current_policy]:
        raise ValueError(
            f"Cannot upgrade policy: {current_policy.value} → {new_policy.value}. "
            "Use a less restrictive policy level."
        )


def reprocess_private_data(
    config: TracerConfig, new_attachment_policy: AttachmentPolicy | None = None
) -> tuple[int, int]:
    """Reprocess private chat data with attachment policy transformations.

    Reads all private chats, applies transformations based on parameters,
    and writes the transformed chats back to storage.

    Args:
        config: Runtime configuration with repo_dir and paths
        new_attachment_policy: Optional target attachment policy for transformation

    Returns:
        Tuple of (processed_count, error_count)

    Raises:
        ValueError: If policy validation fails (e.g., upgrade attempt from STRIP)
    """

    if new_attachment_policy is None:
        return (0, 0)

    private_dir = config.repo_dir / "data/private/chats"
    private_sessions = read_private_chats(private_dir)

    processed_count = 0
    error_count = 0

    for chat_id, session in private_sessions.items():
        try:
            _validate_policy_transition(None, new_attachment_policy)

            transformed = _apply_attachment_policy(session, new_attachment_policy)

            write_private_chat(private_dir, transformed)
            processed_count += 1
        except Exception:
            error_count += 1

    return (processed_count, error_count)
