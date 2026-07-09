# Dockerfile — Docker fallback for reproducible builds
# Use when Nix is not available.

FROM texlive/texlive:TL2024-historic

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-yaml \
    ghostscript \
    librsvg2-bin \
    nodejs \
    npm \
    chktex \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Python packages for build orchestration + templating.
# The texlive base ships an externally-managed Python (PEP 668), so this
# system-wide install needs an explicit override.
RUN pip3 install --no-cache-dir --break-system-packages jinja2

# Mermaid CLI for diagram generation
RUN npm install -g @mermaid-js/mermaid-cli

# Working directory
WORKDIR /workspace
COPY . /workspace

# Default command: build all documents in draft mode
CMD ["python3", "-m", "inclusio.cli.build", "build", "--mode", "draft"]
