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
        ENABLE_NOTIFICATIONS = "true";
        NOTIFICATION_BATCH_TIMEOUT = "30";
      };
      description = "Environment variables for the service";
    };

    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      example = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
      description = ''
        Path to environment file containing sensitive variables like IMMICH_API_KEY.
        Set to null to disable environment file loading.
        This file should contain:
        IMMICH_API_KEY=your_api_key_here
        
        Note: The file must exist when the service starts, or the service will fail.
        Use the settings option for non-sensitive configuration instead.
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

    # Create example environment file
    home.file.".config/immich-auto-uploader/.env.example" = {
      text = ''
        # Immich Auto-Uploader Environment Configuration
        # Copy this file to .env and fill in your values
        
        # REQUIRED: Immich server connection
        IMMICH_API_URL=https://your-immich-instance.com
        IMMICH_API_KEY=your_api_key_here
        
        # OPTIONAL: Directory settings (these have defaults)
        # WATCH_DIRECTORIES=${config.home.homeDirectory}/Downloads
        # ARCHIVE_DIRECTORY=${config.home.homeDirectory}/Pictures/Archived  
        
        # OPTIONAL: Behavior settings
        # WATCH_RECURSIVE=true
        # LOG_LEVEL=INFO
        # FILE_STABILITY_WAIT_SECONDS=5
        # FILE_STABILITY_CHECK_INTERVAL=1.0
        # MAX_FILE_SIZE_MB=1000
        # SUPPORTED_EXTENSIONS=jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp
        
        # OPTIONAL: Notification settings
        # ENABLE_NOTIFICATIONS=true
        # NOTIFICATION_BATCH_TIMEOUT=30
        
        # NOTE: You can also configure these settings using the Home Manager
        # 'settings' option instead of this file. Use this file only for
        # sensitive values like IMMICH_API_KEY.
      '';
    };

    # Create setup instructions
    home.file.".config/immich-auto-uploader/README.txt" = {
      text = ''
        Immich Auto-Uploader Setup Instructions
        ======================================
        
        1. Copy .env.example to .env:
           cp ~/.config/immich-auto-uploader/.env.example ~/.config/immich-auto-uploader/.env
        
        2. Edit .env file with your Immich server details:
           - Set IMMICH_API_URL to your Immich server URL
           - Set IMMICH_API_KEY to your API key (get from Immich web interface)
        
        3. Update your Home Manager configuration to set environmentFile:
           services.immich-auto-uploader = {
             enable = true;
             environmentFile = "~/.config/immich-auto-uploader/.env";
             settings = {
               # Configure non-sensitive settings here
             };
           };
        
        4. Rebuild Home Manager:
           home-manager switch
        
        5. Check service status:
           systemctl --user status immich-auto-uploader
        
        Troubleshooting:
        - Check logs: journalctl --user -u immich-auto-uploader -f
        - Ensure .env file exists and has correct permissions
        - Verify Immich server is accessible and API key is valid
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
        
        # Restart on failure, but not too aggressively
        StartLimitBurst = 5;
        StartLimitIntervalSec = 300;
        
        # Environment variables from settings
        Environment = mapAttrsToList (name: value: "${name}=${value}") cfg.settings;
        
        # Load sensitive environment variables from file
        EnvironmentFile = mkIf (cfg.environmentFile != null) cfg.environmentFile;
        
        # Logging configuration
        StandardOutput = "journal";
        StandardError = "journal";
        SyslogIdentifier = "immich-auto-uploader";
        
        # Working directory
        WorkingDirectory = "${config.home.homeDirectory}";
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