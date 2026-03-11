# Public Private Boundary

## Public (`euxis-publisher`)

- Engine code (`core/`, `scripts/`)
- Packaged Python logic (`euxis_publisher/`)
- Public tests and CI configuration
- Generic non-sensitive fixtures used only for engine validation
- Public documentation

## Private (`euxis-publisher-private`)

- Real document sources (`src/`)
- Real metadata and content datasets (`data/`)
- Proprietary templates and assets
- Content-specific QA and linguistic checks

## Rule

If a file can reveal proprietary content, filing strategy, client details, or personal data, it must be kept in the private repository.
