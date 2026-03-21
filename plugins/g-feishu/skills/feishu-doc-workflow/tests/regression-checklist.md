# feishu-doc-workflow Regression Checklist

## Purpose

Keep a minimal, repeatable regression set inside the skill directory so the skill remains portable.

## Static Checks

Run from the repository root.

Run after any module split, import cleanup, or logic change:

```bash
python3 -m py_compile \
  .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py \
  .agents/skills/feishu-doc-workflow/scripts/feishu_doc_runtime/*.py
```

```bash
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py create-doc --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py update-doc --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py import-doc --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py fetch-content --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py share-doc --help
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py get-comments --help
```

## Planner Smoke Test

```bash
python3 .agents/skills/feishu-doc-workflow/scripts/feishu_doc_helper.py \
  api-plan \
  --operation create \
  --markdown-file <your_markdown_file>
```

Expect:
- `routing_decision.workflow_kind = direct_text_write`
- `preferred_entrypoint = create-doc`

## Real Execution Smoke Test

Resolve a user token first using skill `feishu-auth-and-scopes`:

```
Use skill feishu-auth-and-scopes resolve-token to get a user token,
then extract access_token from the JSON result.
```

Then run:

1. `create-doc`
2. `update-doc --mode append`
3. `fetch-content`
4. `import-doc`

## Validation Documents

Do not store plaintext doc IDs or document links in this checklist. For each
regression run:

1. Create a fresh validation doc with `create-doc`
2. Update it with `update-doc --mode append`
3. Read it back with `fetch-content`
4. If import is part of the run, create a separate throwaway import doc with
   `import-doc`
5. Return the created links in the current response instead of committing them
   here

Expected content in the create/update validation doc:
- `验证文档`
- `第一行。`
- `追加`
- `第二行。`

Suggested minimal markdown:

```md
# 验证文档

第一行。
```

## High-Risk Areas

Any change touching these modules should also re-run targeted real regression:

- [`scripts/feishu_doc_runtime/convert_ops.py`](../scripts/feishu_doc_runtime/convert_ops.py)
- [`scripts/feishu_doc_runtime/patch_ops.py`](../scripts/feishu_doc_runtime/patch_ops.py)
- [`scripts/feishu_doc_runtime/media_ops.py`](../scripts/feishu_doc_runtime/media_ops.py)

Targeted cases:
- Markdown table creation
- Image upload replacement
- `fetch-content --include-media`
- overwrite diff update
- title/range patch update
- [`scripts/feishu_doc_runtime/media_ops.py`](../scripts/feishu_doc_runtime/media_ops.py)
