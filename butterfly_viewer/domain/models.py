"""Core domain models used across the application."""

from dataclasses import dataclass
from typing import Literal, Optional


OverlayLayoutMode = Literal["left-right", "top-bottom", "quad"]


@dataclass(frozen=True)
class ImageSlot:
    """One logical image slot within a comparison view."""

    title: str
    filepath: Optional[str]


@dataclass(frozen=True)
class ImageMetadata:
    """Basic metadata displayed in the stats sidebar."""

    filename: str
    resolution: str
    depth_channels: str
    file_size: str


@dataclass(frozen=True)
class ImageStatsEntry:
    """Stats entry rendered as a card in the sidebar."""

    title: str
    filename: str
    resolution: str
    depth_channels: str
    file_size: str
