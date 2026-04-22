### CLASSIFICATION RULES (Task Routing)

Apply the following rules to classify each task into exactly one section.
Priority: Устраненные уязвимости > Исправленные ошибки > Изменение функциональности.

---

#### 🔴 Устраненные уязвимости
Include ONLY the CVE* identifier (not full summary).

Condition (ANY of):
- Source: STS, type = BUG_КБ
- Source: SBTSUPPORT, AND task name matches pattern: CVE-\d+-\d+

---

#### 🟡 Исправленные ошибки

Condition (ANY of):
- Source: TSK (all, no exceptions)
- Source: SBTSUPPORT, AND task name does NOT match CVE-\d+-\d+
- Source: STS, type = Bug, AND type ≠ BUG_КБ

---

#### 🟢 Изменение функциональности

Condition (ANY of):
- Source: CRPV, AND task name does NOT match any Citadel pattern (see below)
- Source: STS, type ≠ Bug

---

#### ⛔ Citadel tasks — EXCLUDE from all sections
A CRPV task is a Citadel task if its name matches ANY of:
- /Реализовать требование .* стандарта .*/
- /Пройти ручную проверку на соответствие требованию .* стандарта/
- /Реализовать стандарт/
- /Пройденные требования стандарта/
- /Пройденные требования по стандарту/
- /Нарушение стандарта/

Citadel tasks must NOT appear in any output section.

---

#### CONDITIONAL OUTPUT LOGIC
- If a section has zero qualifying tasks → **OMIT** both the header (##) and the table entirely.
- Never render an empty table or empty header.
- For "Устраненные уязвимости": render only the CVE* identifier per row, not the full task summary.
