"""Reprocess engine for transforming private chat data based on attachment policies."""

import re

from llm_tracer.config import TracerConfig
from llm_tracer.schema import AttachmentPolicy, ChatSession
from llm_tracer.storage import read_private_chats, write_private_chat

"""Public symbols exported by this module."""
__all__ = ("AttachmentPolicy", "reprocess_private_data")


"""Pattern for URI-like attachment references."""
_ATTACHMENT_URI_PATTERN = re.compile(r"\b(?:file|data|https?)://[^\s\"'`}<\]]+")


"""Pattern for likely encoded payload blobs."""
_ENCODED_BLOB_PATTERN = re.compile(r"\b[A-Za-z0-9+/=]{100,}\b")


"""Pattern for inline attachment labels (e.g., `image: foo.png`)."""
_ATTACHMENT_LABEL_PATTERN = re.compile(
    r"\b(?:attachment|file|blob|media|image|video|audio|document):\s*[^\s,;]+",
    flags=re.IGNORECASE,
)


def _rewrite_content(content: str, policy: AttachmentPolicy) -> str:
    """Apply attachment redaction policy to one message content string."""

    if policy == AttachmentPolicy.METADATA_ONLY:
        content = _ATTACHMENT_URI_PATTERN.sub("<ATTACHMENT>", content)
        content = _ENCODED_BLOB_PATTERN.sub("<ENCODED_CONTENT>", content)
        return content
    if policy == AttachmentPolicy.STRIP:
        content = _ATTACHMENT_URI_PATTERN.sub("", content)
        content = _ENCODED_BLOB_PATTERN.sub("", content)
        content = _ATTACHMENT_LABEL_PATTERN.sub("", content)
        return content
    return content


def _apply_attachment_policy(
    session: ChatSession, policy: AttachmentPolicy
) -> ChatSession:
    """Return a copy of *session* with attachments removed or reduced per *policy*."""

    if policy == AttachmentPolicy.FULL:
        return session

    transformed_messages = []
    for message in session.messages:
        new_content = _rewrite_content(message.content, policy)

        transformed_messages.append(
            message.model_copy(update={"content": new_content.strip()})
        )

    return session.model_copy(update={"messages": transformed_messages})


def reprocess_private_data(
    config: TracerConfig, new_attachment_policy: AttachmentPolicy | None = None
) -> tuple[int, int]:
    """Apply *new_attachment_policy* to every private chat; return (processed, errors)."""

    if new_attachment_policy is None:
        return (0, 0)

    private_dir = config.repo_dir / "data/private/chats"
    private_sessions = read_private_chats(private_dir)

    processed_count = 0
    error_count = 0

    for session in private_sessions.values():
        try:
            transformed = _apply_attachment_policy(session, new_attachment_policy)

            write_private_chat(private_dir, transformed)
            processed_count += 1
        except Exception:
            error_count += 1

    return (processed_count, error_count)
