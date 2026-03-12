from __future__ import annotations

"""Whiteboard seed helpers for plain text, Mermaid, and PlantUML blocks."""

import json

from .common import http_json, raise_for_lark_failure


def create_whiteboard_text_seed(whiteboard_id: str, seed_text: str, bearer_token: str) -> dict[str, object]:
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(
            {
                "nodes": [
                    {
                        "type": "text_shape",
                        "x": 80,
                        "y": 80,
                        "width": 640,
                        "height": 160,
                        "text": {
                            "text": seed_text,
                            "font_size": 18,
                        },
                    }
                ]
            },
            ensure_ascii=True,
        ).encode("utf-8"),
    )
    raise_for_lark_failure("create whiteboard text seed", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def create_whiteboard_code_seed(
    whiteboard_id: str,
    diagram_code: str,
    bearer_token: str,
    *,
    syntax_type: int = 1,
    style_type: int | None = None,
    diagram_type: int | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "plant_uml_code": diagram_code,
        "syntax_type": syntax_type,
    }
    if isinstance(style_type, int):
        body["style_type"] = style_type
    if isinstance(diagram_type, int):
        body["diagram_type"] = diagram_type
    status, payload, text = http_json(
        f"https://open.feishu.cn/open-apis/board/v1/whiteboards/{whiteboard_id}/nodes/plantuml",
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body, ensure_ascii=True).encode("utf-8"),
    )
    raise_for_lark_failure("create whiteboard diagram seed", status, payload, text)
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def seed_created_whiteboards(
    descendants: list[dict[str, object]],
    create_result: dict[str, object],
    bearer_token: str,
) -> list[dict[str, object]]:
    temp_seed_map: dict[str, dict[str, object]] = {}
    for block in descendants:
        block_id = block.get("block_id")
        seed_kind = block.get("_codex_whiteboard_seed_kind")
        seed_text = block.get("_codex_whiteboard_seed_text")
        plantuml_code = block.get("_codex_whiteboard_plantuml_code")
        if isinstance(block_id, str) and isinstance(seed_text, str) and seed_text.strip():
            temp_seed_map[block_id] = {
                "kind": "text",
                "seed_text": seed_text.strip(),
            }
        elif isinstance(block_id, str) and isinstance(plantuml_code, str) and plantuml_code.strip():
            temp_seed_map[block_id] = {
                "kind": str(seed_kind or "plantuml"),
                "diagram_code": plantuml_code.strip(),
                "syntax_type": block.get("_codex_whiteboard_plantuml_syntax_type"),
                "style_type": block.get("_codex_whiteboard_plantuml_style_type"),
                "diagram_type": block.get("_codex_whiteboard_plantuml_diagram_type"),
            }
    if not temp_seed_map:
        return []

    temp_to_real: dict[str, str] = {}
    relations = create_result.get("block_id_relations")
    if isinstance(relations, list):
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            temp_id = relation.get("temporary_block_id")
            real_id = relation.get("block_id")
            if isinstance(temp_id, str) and isinstance(real_id, str):
                temp_to_real[temp_id] = real_id

    real_to_board_token: dict[str, str] = {}
    children = create_result.get("children")
    if isinstance(children, list):
        for child in children:
            if not isinstance(child, dict) or child.get("block_type") != 43:
                continue
            block_id = child.get("block_id")
            board = child.get("board")
            if not isinstance(block_id, str) or not isinstance(board, dict):
                continue
            token = board.get("token")
            if isinstance(token, str) and token:
                real_to_board_token[block_id] = token

    results: list[dict[str, object]] = []
    for temp_id, seed_payload in temp_seed_map.items():
        real_id = temp_to_real.get(temp_id)
        if not real_id:
            results.append(
                {
                    "temporary_block_id": temp_id,
                    "status": "skipped",
                    "reason": "missing_block_relation",
                }
            )
            continue
        whiteboard_id = real_to_board_token.get(real_id)
        if not whiteboard_id:
            results.append(
                {
                    "temporary_block_id": temp_id,
                    "block_id": real_id,
                    "status": "skipped",
                    "reason": "missing_whiteboard_token",
                }
            )
            continue
        seed_kind = str(seed_payload.get("kind") or "text")
        if seed_kind in {"plantuml", "mermaid"}:
            diagram_code = str(seed_payload.get("diagram_code") or "").strip()
            if not diagram_code:
                results.append(
                    {
                        "temporary_block_id": temp_id,
                        "block_id": real_id,
                        "whiteboard_id": whiteboard_id,
                        "status": "skipped",
                        "reason": "missing_diagram_code",
                    }
                )
                continue
            seed_result = create_whiteboard_code_seed(
                whiteboard_id,
                diagram_code,
                bearer_token,
                syntax_type=int(seed_payload.get("syntax_type") or 1),
                style_type=int(seed_payload["style_type"]) if isinstance(seed_payload.get("style_type"), int) else None,
                diagram_type=int(seed_payload["diagram_type"]) if isinstance(seed_payload.get("diagram_type"), int) else None,
            )
        else:
            seed_text = str(seed_payload.get("seed_text") or "").strip()
            if not seed_text:
                results.append(
                    {
                        "temporary_block_id": temp_id,
                        "block_id": real_id,
                        "whiteboard_id": whiteboard_id,
                        "status": "skipped",
                        "reason": "missing_seed_text",
                    }
                )
                continue
            seed_result = create_whiteboard_text_seed(whiteboard_id, seed_text, bearer_token)
        results.append(
            {
                "temporary_block_id": temp_id,
                "block_id": real_id,
                "whiteboard_id": whiteboard_id,
                "status": "seeded",
                "seed_kind": seed_kind,
                **({"seed_text": seed_payload.get("seed_text")} if seed_kind == "text" else {}),
                **({"diagram_code": seed_payload.get("diagram_code")} if seed_kind in {"plantuml", "mermaid"} else {}),
                "seed_result": seed_result,
            }
        )
    return results
