# UI component layer

Shared page primitives live here. Pages should compose these components instead
of recreating headers, modal overlays, form labels, alerts, empty states,
filters, search fields, or status badges.

- `PageHeader` — page title, subtitle, and action slot
- `ModalShell` — accessible modal frame with optional form and footer
- `FormField` — label, hint, required marker, error, and control slot
- `AlertBanner` / `EmptyState` / `StatusBadge` — application feedback states
- `FilterDropdown` / `SearchInput` — list filtering controls

Low-level Volt controls (`Button`, `InputText`, `Textarea`, `Select`, and
`IconButton`) live in `src/volt`. Workflow-specific reusable editors live in
`src/components/designer`.
