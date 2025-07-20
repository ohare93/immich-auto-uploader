{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.immich-auto-uploader;
  
  # Import the package
  immich-auto-uploader = pkgs.callPackage ./package.nix { };

in {
  options.services.immich-auto-uploader = {
    enable = mkEnableOption "Immich Auto-Uploader service";

    package = mkOption {
      type = types.package;
      default = immich-auto-uploader;
      description = "The immich-auto-uploader package to use";
    };

    settings = mkOption {
      type = types.attrsOf types.str;
      default = {};
      example = {
        IMMICH_API_URL = "https://immich.example.com";
        WATCH_DIRECTORIES = "${config.home.homeDirectory}/Downloads,${config.home.homeDirectory}/Pictures/Import";
        ARCHIVE_DIRECTORY = "${config.home.homeDirectory}/Pictures/Archived";
        LOG_LEVEL = "INFO";
        FILE_STABILITY_WAIT_SECONDS = "5";
        FILE_STABILITY_CHECK_INTERVAL = "1.0";
        MAX_FILE_SIZE_MB = "1000";
        SUPPORTED_EXTENSIONS = "jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp";
      };
      description = "Environment variables for the service";
    };

    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
      example = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
      description = ''
        Path to environment file containing sensitive variables like IMMICH_API_KEY.
        This file should contain:
        IMMICH_API_KEY=your_api_key_here
      '';
    };

    startAt = mkOption {
      type = types.str;
      default = "";
      example = "hourly";
      description = ''
        When to start the service. Empty string means start immediately and keep running.
        Use systemd calendar event format for scheduled runs (e.g., "hourly", "daily", "weekly").
      '';
    };
  };

  config = mkIf cfg.enable {
    # Install the package
    home.packages = [ cfg.package ];

    # Create config directory
    home.file.".config/immich-auto-uploader/.keep".text = "";

    # Create example environment file if it doesn't exist
    home.file.".config/immich-auto-uploader/.env.example" = {
      text = ''
        # Copy this file to .env and fill in your values
        IMMICH_API_URL=https://your-immich-instance.com
        IMMICH_API_KEY=your_api_key_here
        
        # Optional settings (these have defaults)
        # WATCH_DIRECTORIES=${config.home.homeDirectory}/Downloads
        # ARCHIVE_DIRECTORY=${config.home.homeDirectory}/Pictures/Archived  
        # LOG_LEVEL=INFO
        # FILE_STABILITY_WAIT_SECONDS=5
        # FILE_STABILITY_CHECK_INTERVAL=1.0
        # MAX_FILE_SIZE_MB=1000
        # SUPPORTED_EXTENSIONS=jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp
      '';
    };

    # Systemd user service
    systemd.user.services.immich-auto-uploader = {
      Unit = {
        Description = "Immich Auto-Uploader - Monitor directories and upload to Immich";
        Documentation = "https://github.com/your-username/immich-auto-uploader";
        After = [ "network-online.target" ];
        Wants = [ "network-online.target" ];
      };

      Service = {
        Type = "simple";
        ExecStart = "${cfg.package}/bin/immich-auto-uploader";
        Restart = "always";
        RestartSec = "10s";
        
        # Environment variables from settings
        Environment = mapAttrsToList (name: value: "${name}=${value}") cfg.settings;
        
        # Load sensitive environment variables from file
        EnvironmentFile = mkIf (cfg.environmentFile != null && pathExists cfg.environmentFile) cfg.environmentFile;
        
        # Logging
        StandardOutput = "journal";
        StandardError = "journal";
        SyslogIdentifier = "immich-auto-uploader";
      };

      Install = {
        WantedBy = [ "default.target" ];
      };
    } // (optionalAttrs (cfg.startAt != "") {
      # If startAt is specified, use timer instead of always-on service
      Unit.PartOf = [ "immich-auto-uploader.timer" ];
      Install.WantedBy = mkForce [ ];
    });

    # Optional timer for scheduled runs
    systemd.user.timers.immich-auto-uploader = mkIf (cfg.startAt != "") {
      Unit = {
        Description = "Timer for Immich Auto-Uploader";
        Requires = [ "immich-auto-uploader.service" ];
      };

      Timer = {
        OnCalendar = cfg.startAt;
        Persistent = true;
      };

      Install = {
        WantedBy = [ "timers.target" ];
      };
    };
  };
}