from __future__ import annotations

"""Markdown normalization, Feishu-flavored extensions, and block parsing."""

from .block_serialization import (
    block_to_markdown,
    blocks_to_markdown,
    extract_text_from_elements,
)
from .block_builders import make_text_elements
from .image_refs import (
    extract_markdown_image_sources,
    markdown_contains_images,
    mask_non_rendered_regions,
    normalize_markdown_image_target,
)
from .markdown_parser import (
    is_markdown_table_separator,
    parse_markdown_table_row,
    parse_markdown_to_descendants,
)
from .markdown_preprocess import (
    CALLOUT_END_MARKER,
    CALLOUT_START_MARKER,
    FILE_MARKER,
    GRID_MARKER,
    LARK_TABLE_MARKER,
    WHITEBOARD_MARKER,
    normalize_markdown,
    preprocess_lark_flavored_markdown,
)
from .selection_ops import (
    compute_updated_markdown,
    find_all_ellipsis_occurrences,
    find_all_literal_occurrences,
    join_with_spacing,
    load_markdown_argument,
    parse_heading_line,
    resolve_selection_by_title,
    resolve_selection_with_ellipsis,
    selection_pattern_parts,
    splice_text,
)
