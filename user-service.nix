{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.immich-auto-uploader-user;
  
  # Create Python environment with dependencies
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    requests
    watchdog
    python-dotenv
  ]);
  
  # Create the service script
  serviceScript = pkgs.writeScript "immich-auto-uploader-user" ''
    #!${pkgs.bash}/bin/bash
    cd ${cfg.sourceDirectory}
    exec ${pythonEnv}/bin/python src/main.py
  '';

in {
  options.services.immich-auto-uploader-user = {
    enable = mkEnableOption "Immich Auto-Uploader user service";

    sourceDirectory = mkOption {
      type = types.path;
      default = "${config.home.homeDirectory}/immich-auto-uploader";
      description = "Directory containing the immich-auto-uploader source code";
    };

    environment = mkOption {
      type = types.attrsOf types.str;
      default = {};
      example = {
        IMMICH_API_URL = "https://immich.example.com";
        WATCH_DIRECTORIES = "${config.home.homeDirectory}/Downloads";
        ARCHIVE_DIRECTORY = "${config.home.homeDirectory}/Pictures/Archived";
        LOG_LEVEL = "INFO";
        FILE_STABILITY_WAIT_SECONDS = "5";
        FILE_STABILITY_CHECK_INTERVAL = "1.0";
      };
      description = "Environment variables for the service";
    };

    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      example = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
      description = "Path to environment file containing sensitive variables like IMMICH_API_KEY";
    };
  };

  config = mkIf cfg.enable {
    # User systemd service
    systemd.user.services.immich-auto-uploader = {
      Unit = {
        Description = "Immich Auto-Uploader - Monitor directories and upload to Immich";
        After = [ "network-online.target" ];
        Wants = [ "network-online.target" ];
      };

      Service = {
        Type = "simple";
        WorkingDirectory = cfg.sourceDirectory;
        ExecStart = serviceScript;
        Restart = "always";
        RestartSec = "10s";
        
        # Environment variables
        Environment = mapAttrsToList (name: value: "${name}=${value}") cfg.environment;
      } // (optionalAttrs (cfg.environmentFile != null) {
        EnvironmentFile = cfg.environmentFile;
      });

      Install = {
        WantedBy = [ "default.target" ];
      };
    };

    # Ensure Python environment is available
    home.packages = [ pythonEnv ];
  };
}