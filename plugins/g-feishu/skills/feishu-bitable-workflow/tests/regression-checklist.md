# feishu-bitable-workflow Regression Checklist

## Purpose

Keep a minimal, repeatable regression set inside the skill directory so the
skill remains portable after refactors and migration.

## Static Checks

Run from the repository root.

Run after any module split, import cleanup, or behavior change:

```bash
python3 -m py_compile \
  .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py \
  .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_runtime/*.py
```

```bash
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py create-app --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py create-table --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py create-field --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py create-record --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py create-view --help
python3 .agents/skills/feishu-bitable-workflow/scripts/feishu_bitable_helper.py list-records --help
```

## Sample Inputs

Use temporary local JSON files during regression runs instead of committed fixtures.

## Resolve Token

This skill defaults to user token. Resolve one first:

```bash
python3 .agents/skills/feishu-auth-and-scopes/scripts/feishu_auth_helper.py \
  resolve-token --identity user --print-access-token
```

## Temporary Acceptance Objects

Do not commit plaintext base IDs, table IDs, view IDs, or user IDs into the
skill. For each regression run:

1. Create a temporary app with `create-app`
2. Create one temporary table with `create-table`
3. Create one temporary validation view with `create-view`
4. Record the returned `app_url`, `table_url`, and `view_url` in the current
   session notes if needed
5. Delete throwaway objects when the run finishes, unless the current thread
   explicitly wants to keep them for user inspection

When constructing sample records for `batch-create-records`, use the current
an explicit person `open_id` (resolve by email/name via `feishu-search-and-locate` first when needed) for person fields.

## Real Regression Coverage

### App

Run and verify:

1. `create-app`
2. `get-app`
3. `list-apps`
4. `update-app`
5. `copy-app`

### Table

Run and verify:

1. `create-table`
2. `list-tables`
3. `update-table`
4. `delete-table`
5. `batch-create-tables`
6. `batch-delete-tables`

### Field

Run and verify:

1. `create-field`
2. `list-fields`
3. `update-field`
4. `delete-field`

Recommended field aliases to exercise:

- `text`
- `number`
- `single_select`
- `multi_select`
- `datetime`
- `checkbox`
- `person`
- `phone`
- `link`
- `attachment`

### Record

Run and verify:

1. `create-record`
2. `batch-create-records`
3. `list-records`
4. `update-record`
5. `batch-update-records`
6. `delete-record`
7. `batch-delete-records`

Expected validation table records:

- `任务A`
- `任务B`
- `任务C`

### Empty Record Behavior

This is an explicit regression requirement. `list-records` must return empty
records as `fields: {}` instead of silently filtering them out.

Suggested sequence:

1. Create a temporary JSON file containing empty records, for example:

   ```json
   [
     {"fields": {}},
     {"fields": {}},
     {"fields": {}}
   ]
   ```

2. `batch-create-records --records-file <your_empty_records_json>`
3. `list-records`
4. Confirm the new records are present with empty `fields`
5. `batch-delete-records` to clean them up

### View

Run and verify:

1. `create-view`
2. `get-view`
3. `list-views`
4. `update-view`
5. `delete-view`

## Expected Links

Every write operation should return the stable links needed for follow-up work:

- `app_url`
- `table_url`
- `view_url` when applicable

## Cleanup Rule

Use temporary objects for destructive regression. If the current thread needs a
user-visible artifact, create a fresh validation app during the run and return
its links in the response instead of storing IDs in this file.
