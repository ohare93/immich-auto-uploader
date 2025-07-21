{
  description = "Immich Auto-Uploader - Automatically upload images and videos to Immich";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        immich-auto-uploader = pkgs.callPackage ./package.nix { };
        
      in {
        # Default package
        packages.default = immich-auto-uploader;
        packages.immich-auto-uploader = immich-auto-uploader;

        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python311
            python311Packages.requests
            python311Packages.watchdog
            python311Packages.python-dotenv
            python311Packages.pytest
            python311Packages.pytest-cov
            python311Packages.pytest-mock
          ];
          
          shellHook = ''
            echo "🚀 Immich Auto-Uploader development environment"
            echo "📁 Source code: $(pwd)/src/"
            echo "🐍 Python: $(python --version)"
            echo ""
            echo "Available commands:"
            echo "  python src/main.py          - Run the uploader"
            echo "  python -m py_compile src/*  - Check syntax"
            echo "  pytest                      - Run unit tests"
            echo "  pytest --cov=src           - Run tests with coverage"
            echo ""
            echo "Environment variables needed:"
            echo "  IMMICH_API_URL=https://your-immich-instance.com"
            echo "  IMMICH_API_KEY=your_api_key_here"
            echo ""
            echo "Optional settings:"
            echo "  WATCH_DIRECTORIES=~/Downloads"
            echo "  ARCHIVE_DIRECTORY=~/Pictures/Archived"
            echo "  WATCH_RECURSIVE=true"
            echo "  LOG_LEVEL=INFO"
          '';
        };

        # Application runner
        apps.default = {
          type = "app";
          program = "${immich-auto-uploader}/bin/immich-auto-uploader";
        };

        # Checks for CI/CD
        checks = {
          # Syntax check
          python-syntax = pkgs.runCommand "check-python-syntax" {
            buildInputs = [ pkgs.python311 ];
          } ''
            cd ${./.}
            python -m py_compile src/*.py
            touch $out
          '';
          
          # Package build test
          package-build = immich-auto-uploader;
        };

        # Formatter
        formatter = pkgs.nixpkgs-fmt;
      }
    ) // {
      # NixOS modules
      nixosModules = {
        # System service module
        immich-auto-uploader = import ./nixos-service.nix;
        
        # User service module  
        immich-auto-uploader-user = import ./user-service.nix;
        
        # Home Manager module
        home-manager = import ./home-manager.nix;
      };

      # Overlay for easy integration into existing nixpkgs
      overlays.default = final: prev: {
        immich-auto-uploader = final.callPackage ./package.nix { };
      };
      
      # Templates for easy project setup
      templates = {
        default = {
          path = ./.;
          description = "Immich Auto-Uploader project template";
        };
      };
    };
}