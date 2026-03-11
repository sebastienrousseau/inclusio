# Contributing to Research and Innovations Repository

Thank you for your interest in contributing to this academic publications and patent applications repository. This document provides guidelines for maintaining consistency, quality, and organization across all contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Repository Structure](#repository-structure)
- [Naming Conventions](#naming-conventions)
- [Development Workflow](#development-workflow)
- [LaTeX Guidelines](#latex-guidelines)
- [Build System](#build-system)
- [Submission Guidelines](#submission-guidelines)
- [Quality Standards](#quality-standards)

## Code of Conduct

This project is committed to providing a welcoming and inclusive environment for all contributors. We expect all participants to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the academic community
- Show empathy towards other contributors

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **LaTeX Distribution**: TeX Live (recommended) or MiKTeX
- **Python 3.8+**: For build automation and compression pipelines
- **Git**: For version control
- **Make**: For build system execution
- **Optional**:
  - `pdfinfo` (from poppler-utils) for PDF validation
  - `mermaid-cli` for diagram generation

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sebastienrousseau/Publications.git
   cd Publications
   ```

2. **Install dependencies** (if using Python scripts):
   ```bash
   pip3 install -r requirements.txt  # If requirements.txt exists
   ```

3. **Test the build system**:
   ```bash
   make help      # Display available commands
   make status    # Check repository status
   make all       # Build all documents
   ```

## Repository Structure

The repository follows a strict hierarchical structure:

```
Publications/
├── papers/                    # Academic papers and research
│   ├── figures/              # Shared figures and images
│   ├── build/                # Generated PDFs (git-ignored)
│   ├── backups/              # Document backups
│   ├── Makefile              # Build configuration
│   ├── references.bib        # Shared bibliography
│   └── *.tex                 # LaTeX source files
├── patents/                  # Patent applications
│   ├── patent-application/
│   └── qeap-patent-application/
├── cvs/                      # Curriculum vitae documents
├── faqs/                     # Frequently asked questions
├── guides/                   # User guides and documentation
├── build/                    # Central build output directory
├── archive/                  # Historical documents
├── backups/                  # Repository-wide backups
├── scripts/                  # Build and automation scripts
├── .github/                  # GitHub workflows and templates
├── Makefile                  # Root build system
└── parallel_build.py         # Parallel compilation system
```

### Directory Guidelines

- **Each major section** (papers, patents, cvs, faqs, guides) MUST have its own subdirectory
- **Each subdirectory** MUST contain a `README.md` explaining its contents
- **Build artifacts** are centralized in `build/` directories (git-ignored)
- **Figures and images** should be organized in dedicated `figures/` subdirectories

## Naming Conventions

### File and Directory Naming Standard: kebab-case

**MANDATORY**: All new files and directories MUST use kebab-case naming convention:

#### ✅ Correct Examples
- `quantum-api-security-paper.tex`
- `user-authentication-guide.tex`
- `real-time-speech-recognition.tex`
- `patent-application-v2.tex`
- `figures/system-architecture-diagram.png`

#### ❌ Incorrect Examples
- `quantum_api_security_paper.tex` (snake_case - legacy only)
- `UserAuthenticationGuide.tex` (PascalCase)
- `realTimeSpeechRecognition.tex` (camelCase)
- `PATENT_APPLICATION.tex` (UPPER_CASE)

### Legacy File Handling

**Existing files** using snake_case or other naming conventions MAY remain unchanged to preserve git history and external references. However:

- **New versions** of existing files SHOULD migrate to kebab-case
- **Major revisions** SHOULD use kebab-case naming
- **Cross-references** in LaTeX files MUST be updated when files are renamed

### Specific Naming Rules

1. **LaTeX Files**: `document-name.tex`
2. **Bibliography Files**: `references.bib` or `document-name-references.bib`
3. **Figure Files**: `descriptive-name.{pdf,png,jpg,svg}`
4. **Build Scripts**: `script-name.{py,sh,mk}`
5. **Documentation**: `document-type.md` (e.g., `user-guide.md`)

### Version Naming

For versioned documents, use the format: `document-name-v{MAJOR}.{MINOR}.tex`

Example: `quantum-api-security-paper-v2.1.tex`

## Development Workflow

### Multi-Repository Development

This project is transitioning to a multi-repository architecture. Development workflows differ based on the current migration phase:

#### Current Phase: Monorepo with Package Structure

```bash
# Standard workflow for current state
git clone https://github.com/sebastienrousseau/Publications.git
cd Publications

# Work on specific content areas
cd papers/          # or cvs/, patents/, etc.
# Make changes
make all           # Build locally
cd ..
make split-validate # Ensure changes work with future architecture
```

#### Future Phase: Multi-Repository Ecosystem

##### Individual Repository Development
```bash
# Work on a single repository
git clone https://github.com/seb/publications-papers.git
cd publications-papers

# Install shared dependencies
npm install @publications/build-tools@latest
npm install @publications/config@latest

# Make changes and build
make all
```

##### Cross-Repository Development

When changes span multiple repositories (e.g., updating build tools + content):

```bash
# Set up workspace
mkdir publications-workspace
cd publications-workspace

# Clone relevant repositories
git clone https://github.com/seb/publications-build-tools.git
git clone https://github.com/seb/publications-papers.git

# Link for local development
cd publications-papers
npm link ../publications-build-tools

# Make changes across repositories
# Test locally before committing
```

##### Coordinated Pull Request Process

For changes that affect multiple repositories:

1. **Create Feature Branch** in each affected repository:
   ```bash
   # In publications-build-tools
   git checkout -b feat/improve-pdf-compression

   # In publications-papers
   git checkout -b feat/improve-pdf-compression
   ```

2. **Make Changes** in dependency order (build-tools → config → content):
   ```bash
   # Update build-tools first
   cd publications-build-tools
   # Make changes
   git commit -m "feat(compression): improve PDF optimization algorithm"

   # Update dependent repositories
   cd ../publications-papers
   npm update @publications/build-tools
   # Test with new version
   git commit -m "feat(build): use improved PDF compression"
   ```

3. **Submit Coordinated PRs**:
   - Create PR in `publications-build-tools` first
   - Reference the build-tools PR in content repository PRs
   - Use consistent PR titles: `feat(scope): description [Publications-123]`

4. **Merge Strategy**:
   - Merge build-tools PR first
   - Publish new version to npm
   - Update version references in dependent repositories
   - Merge dependent PRs

##### Cross-Repository Issue Tracking

Use issue templates that specify affected repositories:

```markdown
**Affected Repositories:**
- [ ] publications-build-tools
- [ ] publications-papers
- [ ] publications-config

**Cross-Repo Impact:**
Describe how the change affects multiple repositories...
```

#### Dependency Update Procedures

##### Build Tools Updates

When updating `publications-build-tools`:

1. **Version Strategy**: Follow semantic versioning
   - PATCH: Bug fixes, non-breaking changes
   - MINOR: New features, backward-compatible
   - MAJOR: Breaking changes

2. **Release Process**:
   ```bash
   # In publications-build-tools
   npm version minor
   npm publish
   git push && git push --tags
   ```

3. **Dependent Repository Updates**:
   ```bash
   # Update each content repository
   cd publications-papers
   npm update @publications/build-tools
   make all  # Test build
   git commit -m "build(deps): update build-tools to v1.2.0"
   ```

##### Configuration Updates

When updating `publications-config`:

1. **Template Changes**: Update version and notify content repositories
2. **Breaking Changes**: Coordinate with all content repositories
3. **Migration Guides**: Provide upgrade documentation

##### Security Updates

For security vulnerabilities in shared dependencies:

1. **Priority Order**: Fix in build-tools first
2. **Emergency Process**: All repositories must update within 24 hours
3. **Verification**: Run full test suite across all repositories

### Branch Naming

Use kebab-case for branch names:

- Feature branches: `feat/feature-name`
- Bug fixes: `fix/issue-description`
- Documentation: `docs/update-description`
- Releases: `release/v{VERSION}`

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `build`

**Examples**:
- `feat(papers): add quantum cryptography research paper`
- `fix(build): resolve LaTeX compilation warnings`
- `docs(contributing): update naming conventions`

### Pull Request Process

1. **Create feature branch** from `main`
2. **Make changes** following naming conventions
3. **Build and test locally**:
   ```bash
   make clean
   make all
   make validate
   ```
4. **Update documentation** if needed
5. **Submit pull request** with:
   - Clear description of changes
   - Screenshots of PDF output (if applicable)
   - Build status confirmation

## LaTeX Guidelines

### Document Structure

Every LaTeX document MUST follow this structure:

```latex
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
% Additional packages...

\title{Document Title}
\author{Author Name}
\date{\today}

\begin{document}

\maketitle

% Content sections...

\bibliography{references}
\bibliographystyle{plain}

\end{document}
```

### Style Requirements

- **Encoding**: Always use UTF-8
- **Font size**: 12pt for papers, 10pt for CVs
- **Bibliography**: Use BibTeX with `references.bib`
- **Figures**: Store in `figures/` subdirectory
- **Comments**: Use `%` for code comments, document major sections

### Package Management

- **Required packages** MUST be documented in each document's header
- **Custom commands** SHOULD be defined in a preamble section
- **Avoid** obsolete packages (e.g., use `graphicx` not `graphics`)

## Build System

### Available Commands

The build system provides several make targets:

```bash
make help          # Display all available commands
make all           # Build all documents in all subdirectories
make clean         # Remove all build artifacts
make rebuild       # Clean and rebuild everything
make validate      # Validate generated PDFs
make status        # Show build status across all directories
make parallel      # Use parallel build system
make compress      # Run PDF compression pipeline
make optimize      # Build + compress for optimal output
make all-formats   # Build PDF + DOCX + HTML for all documents
make docx          # Convert all documents to DOCX via Pandoc
make html          # Convert all documents to HTML via Pandoc
make cv            # Generate CVs in all formats with ATS validation
make cv-docx       # Generate ATS-optimized CV DOCX only
make cover-letter  # Generate cover letters in all formats
make templates     # Generate DOCX reference templates
make config        # Merge and validate YAML configurations
```

### Build Process

1. **Individual builds**: Each subdirectory has its own `Makefile`
2. **Central collection**: PDFs are copied to `build/` directory
3. **Validation**: Optional PDF validation with `pdfinfo`
4. **Compression**: Python pipeline for PDF optimization

### Multi-Format Pipeline

The repository supports generating documents in multiple formats via Pandoc:

```bash
# Convert all documents to all formats
make all-formats

# Use pandoc directly for format conversion
pandoc papers/my-paper.tex --from latex --to docx --output build/my-paper.docx
pandoc papers/my-paper.tex --from latex --to html5 --output build/my-paper.html
```

### Template Usage Examples

Each document type uses specific templates for multi-format generation:

#### Papers and Whitepapers
```bash
# Build PDF (default LaTeX)
make -C papers all

# Convert to DOCX with professional styling
pandoc papers/my-paper.tex --from latex --to docx \
  --output build/my-paper.docx \
  --reference-doc=templates/reference.docx

# Convert to HTML with whitepaper template
pandoc papers/my-paper.tex --from latex --to html5 \
  --output build/my-paper.html \
  --template=templates/html/whitepaper.html \
  --css=templates/html/css/document.css \
  --standalone --mathjax --toc
```

#### Patents
```bash
# Build PDF
make -C patents/quantum-safe-api-authentication all

# Convert to DOCX
pandoc patents/quantum-safe-api-authentication/patent.tex \
  --from latex --to docx \
  --output build/patent-application.docx \
  --reference-doc=templates/reference.docx
```

#### CVs (ATS-Optimized)
```bash
# Generate all formats with ATS validation
make cv

# Or use the dedicated script
./scripts/generate-cv.sh all    # PDF + DOCX + HTML + ATS report
./scripts/generate-cv.sh docx   # ATS-optimized DOCX only

# Use the ATS template directly
pandoc templates/cv-ats.tex --from latex --to docx \
  --output build/cv.docx \
  --reference-doc=templates/cv-reference.docx
```

#### Cover Letters
```bash
# Generate all formats
make cover-letter

# Or use the dedicated script
./scripts/generate-cover-letter.sh all
./scripts/generate-cover-letter.sh pdf
```

#### FAQs and Guides
```bash
# Build PDF
make -C faqs all
make -C guides all

# Convert to HTML for web publishing
pandoc faqs/your-faq.tex --from latex --to html5 \
  --output build/faq.html \
  --css=templates/html/css/document.css \
  --standalone --toc
```

### YAML Configuration System

Document metadata is managed through YAML configuration files in `config/`:

```bash
# Merge defaults with document-type config
python3 scripts/merge-config.py cv              # CV config
python3 scripts/merge-config.py whitepaper      # Whitepaper config
python3 scripts/merge-config.py cover-letter    # Cover letter config

# Get a specific config value
python3 scripts/merge-config.py cv --get author.primary.full_name

# Export merged config
python3 scripts/merge-config.py cv --output build/cv-config.yaml
```

### Adding New Documents

To add a new document category:

1. **Create subdirectory** using kebab-case
2. **Add Makefile** following existing patterns (include `latex-build.mk` or `build-common.mk`)
3. **Add README.md** explaining the content
4. **Add YAML config** in `config/` for multi-format metadata
5. **Test build process**: `make -C your-directory all`

## Submission Guidelines

### Before Submitting

- [ ] **Follow naming conventions** (kebab-case for new files)
- [ ] **Build successfully**: `make all` passes without errors
- [ ] **Validate PDFs**: `make validate` shows proper PDF generation
- [ ] **Update documentation** if adding new features
- [ ] **Check file sizes**: Large files (>10MB) need justification
- [ ] **Verify bibliography**: All citations resolve properly

### What to Include

- **Source LaTeX files** (`.tex`)
- **Bibliography files** (`.bib`)
- **Figure files** in appropriate formats
- **Updated README.md** if adding new sections
- **Build configuration** (`Makefile`) for new directories

### What NOT to Include

- **Build artifacts** (`.pdf`, `.aux`, `.log`, etc.)
- **Editor files** (`.vscode/`, temporary files)
- **OS-specific files** (`.DS_Store`, `Thumbs.db`)
- **Large binary files** without prior discussion

## Quality Standards

### Document Requirements

- **Academic integrity**: Proper citations and references
- **Language quality**: Professional writing standard
- **Technical accuracy**: Verified facts and figures
- **Reproducibility**: Build process documented and tested

### PDF Output Standards

- **File size**: Optimized for web distribution
- **Quality**: High-resolution figures and text
- **Accessibility**: Proper PDF structure and metadata
- **Compatibility**: PDF/A compliance when possible

### Code Quality

- **LaTeX formatting**: Consistent indentation and structure
- **Comments**: Explain complex macros or formatting choices
- **Error handling**: Graceful compilation failure messages
- **Performance**: Efficient compilation times

## Getting Help

### Documentation

- **README.md**: Project overview and basic usage
- **Individual README files**: Specific directory documentation
- **Makefile help**: `make help` in any directory

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Request Reviews**: Code-specific feedback

### Common Issues

1. **LaTeX compilation errors**: Check package installation and syntax
2. **Build failures**: Ensure all dependencies are installed
3. **PDF generation issues**: Verify figure paths and references
4. **Naming conflicts**: Follow kebab-case conventions consistently

---

## Appendix: Migration Guide

### Converting Existing Files

When updating existing snake_case files to kebab-case:

1. **Create new file** with kebab-case name
2. **Update internal references** and `\input{}` commands
3. **Update Makefile** targets and dependencies
4. **Test build process** thoroughly
5. **Update documentation** and cross-references

### Example Migration

```bash
# Old file: quantum_api_security_paper.tex
# New file: quantum-api-security-paper.tex

# Update references in other files:
sed -i 's/quantum_api_security_paper/quantum-api-security-paper/g' *.tex

# Update Makefile:
sed -i 's/quantum_api_security_paper.pdf/quantum-api-security-paper.pdf/g' Makefile
```

---

*Designed by Sebastien Rousseau — https://sebastienrousseau.com*

*Engineered with Euxis — Enterprise Unified Execution Intelligence System — https://euxis.co*
