# Public Private Boundary

## Public (`inclusio`)

- Engine code (`core/`, `scripts/`)
- Packaged Python logic (`inclusio/`)
- Public tests and CI configuration
- Generic non-sensitive fixtures used only for engine validation
- Public documentation

## Private (`inclusio-private`)

- Real document sources (`src/`)
- Real metadata and content datasets (`data/`)
- Proprietary templates and assets
- Content-specific QA and linguistic checks

## Rule

If a file can reveal proprietary content, filing strategy, client details, or personal data, it must be kept in the private repository.
