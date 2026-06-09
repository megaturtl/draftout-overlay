{
  description = "Draftout opponent overlay: shows the current opponent's competitive W/D/L";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

    pythonFor = pkgs: pkgs.python3.withPackages (ps: with ps; [tkinter requests watchdog]);
  in {
    # `nix run` launches the overlay directly from the source tree.
    apps = forAllSystems (pkgs: let
      python = pythonFor pkgs;
    in {
      default = {
        type = "app";
        program =
          toString (pkgs.writeShellScript "opponent-overlay"
            ''exec ${python}/bin/python ${self}/src/main.py "$@"'');
      };
    });

    # `nix develop` (or direnv `use flake`) for live editing. The local
    # source is on PYTHONPATH so edits take effect immediately, and an
    # `overlay` command launches main.py.
    devShells = forAllSystems (pkgs: let
      python = pythonFor pkgs;
      overlay =
        pkgs.writeShellScriptBin "overlay"
        ''exec ${python}/bin/python "$PWD/src/main.py" "$@"'';
    in {
      default = pkgs.mkShell {
        packages = [python overlay];
        shellHook = ''
          export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"
        '';
      };
    });
  };
}
