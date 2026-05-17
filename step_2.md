**Step 2. Process bundle issues**

Start this step only after Step 1 is fully completed.

If the `get_tasks` response does not contain `bundle.issues`, skip this step and continue to the next step.

If the `get_tasks` response contains `bundle.issues`, process each issue from `bundle.issues` independently.

Each issue has this structure:

```json
{
  "key": "string",
  "name": "string",
  "link": "string"
}
```

Do not treat example values as real data.

## Processing rules

For each issue in `bundle.issues`, apply the rules in this exact order.

### Rule 1. Ignore SUPPORT issues

If `issue.key` contains `SUPPORT`, ignore this issue completely.

Use case-insensitive matching.

Do not call any tool for this issue.

Do not include this issue in collected release data.

Do not include this issue in the final release notes.

Examples:

| `issue.key` | Action |
|---|---|
| `SUPPORT-123` | Ignore |
| `ABC-SUPPORT-123` | Ignore |
| `support - 3` | Ignore |

### Rule 2. Select tool by issue link

For every issue that was not ignored by Rule 1, select exactly one tool based on `issue.link`.

| Condition | Tool to call |
|---|---|
| `issue.link` contains `portal.works.prod` | `get_unit_details` |
| `issue.link` contains `sberworks` | `get_tickets` |

If `issue.link` contains neither `portal.works.prod` nor `sberworks`, skip this issue.

Do not invent another tool.

Do not call more than one tool for the same issue.

### Rule 3. Call the selected tool

Call the selected tool for each issue individually.

Use `issue.key` exactly as it was returned in `bundle.issues`.

The `key` is an exact identifier, not a display label.

Do not modify, normalize, trim, reformat, or transform `issue.key`.

Do not:

- remove spaces
- replace spaces around hyphens
- normalize hyphens
- change letter case
- translate the key
- apply regex cleanup
- slugify the key

Examples:

| `issue.key` from `bundle.issues` | Must be sent to tool |
|---|---|
| `BD.298 - 1` | `BD.298 - 1` |
| `TASK-123` | `TASK-123` |
| `Task - 123` | `Task - 123` |
| `support - 3` | ignored because it contains `SUPPORT` |

Wrong:

| `issue.key` from `bundle.issues` | Wrong tool argument |
|---|---|
| `BD.298 - 1` | `BD.298-1` |
| `TASK - 123` | `TASK-123` |
| `support - 3` | `support-3` |

### Rule 4. Save collected issue data

Save the result of each successful tool call as `collected_issue_data`.

Each collected item must preserve:

- original `issue.key`
- original `issue.name`
- original `issue.link`
- selected tool name
- tool response

Continue processing until all `bundle.issues` have been checked.

## Result of Step 2

After Step 2 is completed, the workflow must have:

- ignored all issues whose `key` contains `SUPPORT`
- called `get_unit_details` for each non-SUPPORT issue whose `link` contains `portal.works.prod`
- called `get_tickets` for each non-SUPPORT issue whose `link` contains `sberworks`
- skipped unsupported links
- preserved all original issue keys exactly as received
- saved all successful tool responses into `collected_issue_data`
