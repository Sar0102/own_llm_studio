### Step 2.5: Unit Details Collection (Tool Execution)

* **⚠️ MANDATORY TOOL CALL — do not skip.**
* For EACH unit code collected in Step 2 — call GET UNIT DETAILS tool.
* This step is required to build the Component Table in the final report.

  #### Extract from response:

  **Код компонента** → field where type = "sber_component" → value[].name (as-is)

  **Название компонента** → field where type = "version" → value[].name,
  strip version suffix matching: \d+[\d.]+\d+[\w-]*
  Example: "Platform V Gateway Management 4.3.9.6-FH" → "Platform V Gateway Management"

  **Версия** → same type = "version" entry → value[].name,
  extract only token matching: \d+[\d.]+\d+[\w-]*
  Example: "Platform V Gateway Management 4.3.9.6-FH" → "4.3.9.6-FH"

  Each row = one value[] from type = "version",
  paired with type = "sber_component" value[].name by ORDER index.

* Store extracted rows — they will be used in OUTPUT TEMPLATE → Компонентный состав.
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
