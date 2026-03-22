# Feishu Sheets API Reference

## Range Format

Ranges use A1 notation relative to the worksheet:

```
A1        — single cell
A1:C5     — rectangular range
A:C       — entire columns A through C
1:5       — entire rows 1 through 5
```

Ranges are **always relative to a single worksheet** identified by `sheet_id`. The `sheet_id` is obtained via the `query-sheets` command.

## Cell Data Structure (Rich Text 3D Array)

The Sheets API uses a 3-level nested array for cell values:

```
values: [          # rows
  [                # cells in a row
    [              # segments in a cell
      { "type": "text", "text": { "text": "Hello" } },
      { "type": "text", "text": { "text": " World" } }
    ],
    [              # next cell
      { "type": "value", "value": { "value": "42" } }
    ]
  ],
  [                # next row
    ...
  ]
]
```

### Segment Types

| type | structure | description |
|---|---|---|
| `text` | `{"type":"text","text":{"text":"string"}}` | Plain text segment |
| `value` | `{"type":"value","value":{"value":"123"}}` | Numeric value (passed as string) |
| `url` | `{"type":"url","url":{"text":"label","link":"https://..."}}` | Hyperlink |
| `mention_user` | `{"type":"mention_user","mention_user":{"user_id":"ou_xxx","user_id_type":"open_id"}}` | @user mention |
| `formula` | `{"type":"formula","formula":{"text":"=SUM(A1:A10)"}}` | Formula |

### Simple Values Shortcut

The `--simple-values` flag accepts a simplified 2D JSON array and auto-converts:

```json
[["Name", "Score"], ["Alice", 95], ["Bob", null]]
```

Conversion rules:
- **string** -> `[{"type":"text","text":{"text":"value"}}]`
- **number** (int/float) -> `[{"type":"value","value":{"value":"123"}}]`
- **null** -> `[]` (empty cell, skipped)

## API Endpoints

### Spreadsheet Level

| Operation | Method | Path |
|---|---|---|
| Create spreadsheet | POST | `/sheets/v3/spreadsheets` |
| Get spreadsheet info | GET | `/sheets/v3/spreadsheets/{spreadsheet_token}` |
| Query worksheets | GET | `/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query` |

### Worksheet Level

| Operation | Method | Path |
|---|---|---|
| Create worksheet | POST | `/sheets/v3/spreadsheets/{spreadsheet_token}/sheets` |
| Copy worksheet | POST | `/sheets/v2/spreadsheets/{spreadsheet_token}/sheets_batch_update` |
| Delete worksheet | POST | `/sheets/v2/spreadsheets/{spreadsheet_token}/sheets_batch_update` |

### Cell Values

| Operation | Method | Path |
|---|---|---|
| Batch read | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/values/batch_get` |
| Batch write | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/values/batch_update` |
| Insert rows | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/values/{range}/insert` |
| Append rows | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/values/{range}/append` |
| Batch clear | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/values/batch_clear` |

### Find & Replace

| Operation | Method | Path |
|---|---|---|
| Find | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/find` |
| Replace | POST | `/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/replace` |

## Limits

- `batch_update` / `batch_get` / `batch_clear`: max 10 ranges per request
- Write operations: max 5000 cells per request
- Cell content: max 40,000 characters per cell
- `replace`: max 5000 cells affected per request
