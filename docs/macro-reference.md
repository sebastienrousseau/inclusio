# Macro Reference

Canonical macro contract for `inclusio` class files.

## Academic and Research

Supported by `pub-paper`, `pub-preprint`, `pub-arxiv`.

- `\affiliation{text}`
- `\keywords{tags}`
- `\arxivid{ID}` (`pub-arxiv`)
- `\correspondingauthor{email}` (`pub-preprint`)

## Legal and Patents

Supported by `pub-patent`, `pub-patent-us`.

- `\patentParagraph{text}`
- `\independentClaim{label}{text}`
- `\dependentClaim{label}{text}{parent}`
- `\priorityClaim`
- `\inventorDeclaration`

## Technical Documentation

Supported by `pub-guide`.

- `\setDocType{text}`
- `\setCodeLanguage{lang}`
- `\setCompanyName{name}`

## Biography and Personal

Supported by `pub-bio`.

- `\bioheader[photo]{Name}{Title}{Affiliation}`
- `\biocontact{email}{url}{orcid}`
- `\subjectarea{tag}`

## Layout Notes

- Class-level `\maketitle` is intentionally redefined per class for role-specific title rendering.
- Header geometry is class-specific; e.g. `pub-guide` uses larger `headheight` than patent classes to avoid header overflow.
