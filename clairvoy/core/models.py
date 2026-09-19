"""
Clairvoy Domain Models
Strongly typed data schemas using Pydantic.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MatchType(str, Enum):
    EXACT_HASH = "EXACT_HASH"
    VISUAL_AI_NEAR_DUPLICATE = "VISUAL_AI_NEAR_DUPLICATE"
    CONTENT_NEAR_DUPLICATE = "CONTENT_NEAR_DUPLICATE"


class ImageCategory(str, Enum):
    PHOTO = "PHOTO"
    SCREENSHOT = "SCREENSHOT"
    DOCUMENT = "DOCUMENT"
    GRAPHIC = "GRAPHIC"
    FILE = "FILE"


class ActionType(str, Enum):
    KEEP = "KEEP"
    DUPLICATE = "DUPLICATE"


class FileEntry(BaseModel):
    """Represents a discovered file in the scan path."""
    path: str
    size_bytes: int
    is_media: bool = False
    quick_hash: str | None = None
    full_sha256: str | None = None
    keeper_score: int = 100
    category: ImageCategory = ImageCategory.FILE


class DuplicateRecord(BaseModel):
    """Flat record format for CSV output and UI display."""
    group_id: int
    match_type: MatchType
    action: ActionType
    similarity: str = "100%"
    similarity_score: float = 1.0
    size_mb: float
    path: str
    dimensions: str | None = None
    category: ImageCategory = ImageCategory.FILE


class DuplicateGroup(BaseModel):
    """Logical cluster of duplicates with a designated keeper and redundant items."""
    group_id: int
    match_type: MatchType
    keeper: DuplicateRecord
    duplicates: list[DuplicateRecord]
    wasted_bytes: int = 0


class ScanSummary(BaseModel):
    """Comprehensive summary returned after an engine run."""
    scanned_paths: list[str] = Field(default_factory=list)
    scanned_dir: str = ""
    total_files_scanned: int
    media_files_scanned: int
    exact_duplicate_groups: int
    visual_ai_groups: int
    content_duplicate_groups: int = 0
    total_duplicate_groups: int
    wasted_bytes: int
    wasted_mb: float
    wasted_gb: float
    duration_seconds: float
    csv_report: str
    summary_json: str
    quarantine_script: str
    groups: list[DuplicateRecord] = Field(default_factory=list)
    category_breakdown: dict[str, int] = Field(default_factory=dict)


class QuarantineItem(BaseModel):
    original_path: str
    quarantined_path: str
    size_bytes: int
    group_id: int


class QuarantineManifest(BaseModel):
    timestamp: str
    base_dirs: list[str] = Field(default_factory=list)
    base_dir: str = ""
    quarantine_dir: str
    total_files_moved: int
    total_bytes_moved: int
    items: list[QuarantineItem] = Field(default_factory=list)


class DeletionItem(BaseModel):
    original_path: str
    size_bytes: int
    group_id: int
    mode: str = "trash"  # "trash" | "permanent"
    trash_path: str | None = None


class DeletionManifest(BaseModel):
    timestamp: str
    mode: str  # "trash" | "permanent"
    base_dirs: list[str] = Field(default_factory=list)
    total_files_deleted: int
    total_bytes_freed: int
    items: list[DeletionItem] = Field(default_factory=list)
    audit_file: str | None = None

