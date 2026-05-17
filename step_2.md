*Step 2. Process bundle issues**

Start this step only after Step 1 is fully completed.

If the `get_tasks` response does not contain `bundle.issues`, skip this step.

For each issue in `bundle.issues`, use this structure:

```json
{
  "key": "string",
  "name": "string",
  "link": "string"
}
```

## Rules

Apply rules in this exact order.

### 1. Ignore SUPPORT

If `issue.key` contains `SUPPORT`, ignore this issue completely.

Use case-insensitive matching.

Do not call any tool for this issue.

Do not extract numbers from this issue.

Examples:

| `issue.key` | Action |
|---|---|
| `SBTSUPPORT - 20702` | Ignore |
| `SBTSUPPORT - 29749` | Ignore |
| `support - 3` | Ignore |

### 2. Select tool by link

For every non-SUPPORT issue, select the tool only by `issue.link`.

| `issue.link` condition | Tool |
|---|---|
| contains `portal.works.prod` | `get_unit_details` |
| contains `sberworks` | `get_tickets` |
| missing or unsupported | skip |

Do not select tools by `issue.key`, `issue.name`, or guessed source.

### 3. Pass original key

Call the selected tool with the original full `issue.key`.

Do not modify `issue.key`.

Do not:

- extract numbers
- remove prefixes
- remove spaces
- normalize hyphens
- change letter case
- convert to integer

Correct:

| `issue.key` pattern | `issue.link` pattern | Action |
|---|---|---|
| `<LETTERS>-<DIGITS>` | `https://sberworks/...` | `get_tickets(["<LETTERS>-<DIGITS>"])` |
| `<LETTERS>-<DIGITS>` | `https://portal.works.prod/...` | `get_unit_details(["<LETTERS>-<DIGITS>"])` |
| `<LETTERS>SUPPORT<LETTERS/SPACE/HYPHEN/DIGITS>` | any link | Ignore |

Examples of valid original keys:

| Original `issue.key` | Meaning |
|---|---|
| `CRPV-47325` | pass exactly as `CRPV-47325` |
| `STS-216122` | pass exactly as `STS-216122` |
| `TASK-123` | pass exactly as `TASK-123` |
| `SBTSUPPORT - 20702` | ignore because it contains `SUPPORT` |

Wrong:

| Wrong input | Reason |
|---|---|
| `get_tickets([20702])` | Extracted number from SUPPORT issue |
| `get_tickets(["47325"])` | Extracted only digits from `<LETTERS>-<DIGITS>` |
| `get_tickets(["<DIGITS>"])` | Must use full original key, not only digits |
| `get_tickets(["SBTSUPPORT - 20702"])` | SUPPORT issue must be ignored |

## Result

After Step 2:

- all SUPPORT issues are ignored
- each non-SUPPORT issue is routed by `link`
- `sberworks` issues go to `get_tickets`
- `portal.works.prod` issues go to `get_unit_details`
- all tool arguments use original full `issue.key`
