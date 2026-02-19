{
  description = "Publications — Publisher-grade LaTeX document system";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # TeX Live (full distribution for maximum compatibility)
            texliveFull

            # Build orchestrator
            python3
            python3Packages.pyyaml
            python3Packages.pytest
            python3Packages.jinja2

            # Asset pipeline
            nodePackages.mermaid-cli   # mmdc: MMD → SVG
            librsvg                    # rsvg-convert: SVG → PDF/PNG

            # Document conversion
            pandoc

            # PDF optimization
            ghostscript

            # Quality tools
            vale                       # Prose linting
            chktex                     # LaTeX linting
          ];

          shellHook = ''
            echo "Publications dev shell ready."
            echo "  make all    — build all documents (draft mode)"
            echo "  make final  — build all documents (camera-ready, PDF/A)"
            echo "  make assets — run asset pipeline"
            echo "  make lint   — run quality checks"
            echo "  make test   — run test suite"
          '';
        };
      }
    );
}
