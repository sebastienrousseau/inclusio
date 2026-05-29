{
  description = "Inclusio — Public document publishing engine";

  inputs = {
    # Bumped from nixos-24.05 (May-2024) on 2026-05-27.
    # texliveFull on 25.05 ships tagpdf >=1.0 (released 2026-04-24);
    # the shellHook below verifies availability either way.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
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
            # TeX Live runtime for public engine development.
            # texliveFull includes tagpdf; shellHook verifies availability.
            texliveFull

            # Build orchestrator
            python3
            python3Packages.pyyaml
            python3Packages.pytest
            python3Packages.jinja2

            # Asset pipeline
            nodePackages.mermaid-cli
            librsvg

            # Document conversion
            pandoc

            # PDF optimization
            ghostscript

            # Quality tools
            vale
            chktex
          ];

          shellHook = ''
            echo "Inclusio dev shell ready."
            if kpsewhich tagpdf.sty >/dev/null 2>&1; then
              echo "  tagpdf: available"
            else
              echo "  tagpdf: MISSING (install TeX package 'tagpdf' for PDF/UA tagging)"
            fi
            echo "  make test   — run public engine tests"
            echo "  make lint   — run quality checks"
          '';
        };
      }
    );
}
