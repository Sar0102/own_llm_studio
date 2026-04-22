### COMPONENT TABLE EXTRACTION RULES

The component table is built by joining two fields from unit details:

**Column: Код компонента**
- Source field: where `type = "sber_component"`
- Value: `value[].name` → use AS-IS (e.g. "SRGE")

**Column: Название компонента**
- Source field: where `type = "version"`
- Value: `value[].name` → extract ONLY words, strip version pattern
- Strip rule: remove trailing token matching pattern \d+[\d.]+\d+
- Example: "Platform V Frontend High Load 4.3.9.6" → "Platform V Frontend High Load"
- Example: "Platform V Gateway Management 4.3.9.6-FH" → "Platform V Gateway Management"

**Column: Версия**
- Source field: same `type = "version"` entry as above
- Value: `value[].name` → extract ONLY version token matching pattern \d+[\d.]+\d+[\w-]*
- Example: "Platform V Frontend High Load 4.3.9.6" → "4.3.9.6"
- Example: "Platform V Gateway Management 4.3.9.6-FH" → "4.3.9.6-FH"

**Row joining rule:**
Each row = one entry from `type = "version"` value[],
paired with the corresponding `type = "sber_component"` value[].name
by matching ORDER or positional index.
---





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
