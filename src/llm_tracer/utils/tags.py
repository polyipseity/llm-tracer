"""Tag normalization and validation utilities."""

"""Public symbols exported by this module."""
__all__ = ("normalize_tag", "normalize_tags")


def normalize_tag(tag: str) -> str:
    """Validate and normalize one hierarchical tag string.

    A tag is a slash-delimited path where each component is non-empty and does
    not contain either slash character itself.
    """

    components = tag.split("/")
    if not components:
        raise ValueError("tag cannot be empty")
    normalized_components: list[str] = []
    for component in components:
        if not component:
            raise ValueError(f"tag {tag!r} contains an empty path component")
        if "/" in component or "\\" in component:
            raise ValueError(
                f"tag component {component!r} cannot contain '/' or '\\\\'"
            )
        normalized_components.append(component.strip())
    return "/".join(normalized_components)


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize, de-duplicate, and sort a tag list for deterministic storage."""

    unique = {normalize_tag(tag) for tag in tags}
    return sorted(unique)
