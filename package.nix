{ lib
, stdenv
, python311
, python311Packages
, makeWrapper
}:

let
  pythonEnv = python311.withPackages (ps: with ps; [
    requests
    watchdog
    python-dotenv
  ]);
  
in stdenv.mkDerivation rec {
  pname = "immich-auto-uploader";
  version = "1.0.0";

  src = ./.;

  nativeBuildInputs = [ makeWrapper ];
  
  buildInputs = [ pythonEnv ];

  installPhase = ''
    runHook preInstall
    
    # Create directory structure
    mkdir -p $out/bin
    mkdir -p $out/lib/immich-auto-uploader
    
    # Copy source files
    cp -r src/ $out/lib/immich-auto-uploader/
    
    # Create wrapper script
    makeWrapper ${pythonEnv}/bin/python $out/bin/immich-auto-uploader \
      --add-flags "$out/lib/immich-auto-uploader/src/main.py" \
      --set PYTHONPATH "$out/lib/immich-auto-uploader/src:$PYTHONPATH"
    
    runHook postInstall
  '';

  # Skip build phase since we're just copying Python files
  dontBuild = true;
  
  # Don't strip Python files
  dontStrip = true;

  meta = with lib; {
    description = "Automatically upload images and videos to Immich server";
    longDescription = ''
      Immich Auto-Uploader monitors directories for new image and video files,
      uploads them to a self-hosted Immich instance, and archives the uploaded files.
      Features real-time file monitoring, file stability detection to prevent
      uploading partial files, and robust error handling.
    '';
    homepage = "https://github.com/your-username/immich-auto-uploader";
    license = licenses.mit;
    maintainers = [ ];
    platforms = platforms.unix;
    mainProgram = "immich-auto-uploader";
  };
}

# Alternative flake-based usage:
# 
# Create a flake.nix file:
#
# {
#   description = "Immich Auto-Uploader";
#
#   inputs = {
#     nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
#     flake-utils.url = "github:numtide/flake-utils";
#   };
#
#   outputs = { self, nixpkgs, flake-utils }:
#     flake-utils.lib.eachDefaultSystem (system:
#       let
#         pkgs = nixpkgs.legacyPackages.${system};
#         immich-auto-uploader = pkgs.callPackage ./package.nix { };
#       in {
#         packages.default = immich-auto-uploader;
#         packages.immich-auto-uploader = immich-auto-uploader;
#
#         apps.default = {
#           type = "app";
#           program = "${immich-auto-uploader}/bin/immich-auto-uploader";
#         };
#       }
#     );
# }