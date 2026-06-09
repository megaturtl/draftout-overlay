{
  description = "Draftout opponent overlay";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

    pythonDeps = ps: [ps.requests ps.watchdog ps.tkinter];
  in {
    # `nix build` / installable on NixOS; exposes the `doverlay` command.
    packages = forAllSystems (pkgs: {
      default = pkgs.python3.pkgs.buildPythonApplication {
        pname = "doverlay";
        version = "0.1.0";
        pyproject = true;
        src = ./.;

        build-system = [pkgs.python3.pkgs.hatchling];
        dependencies = pythonDeps pkgs.python3.pkgs;
      };
    });

    # `nix run` launches the overlay.
    apps = forAllSystems (pkgs: {
      default = {
        type = "app";
        program = "${self.packages.${pkgs.system}.default}/bin/doverlay";
      };
    });

    # `nix develop` (or direnv `use flake`) for editing, building, and testing.
    devShells = forAllSystems (pkgs: {
      default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages pythonDeps)
          pkgs.ruff
          pkgs.ty
        ];
      };
    });
  };
}
