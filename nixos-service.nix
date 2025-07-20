{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.immich-auto-uploader;
  
  # Create Python environment with dependencies
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    requests
    watchdog
    python-dotenv
  ]);
  
  # Create the service script
  serviceScript = pkgs.writeScript "immich-auto-uploader" ''
    #!${pkgs.bash}/bin/bash
    cd ${cfg.workingDirectory}
    exec ${pythonEnv}/bin/python src/main.py
  '';

in {
  options.services.immich-auto-uploader = {
    enable = mkEnableOption "Immich Auto-Uploader service";

    workingDirectory = mkOption {
      type = types.path;
      default = "/var/lib/immich-auto-uploader";
      description = "Working directory for the service";
    };

    user = mkOption {
      type = types.str;
      default = "immich-uploader";
      description = "User to run the service as";
    };

    group = mkOption {
      type = types.str;
      default = "immich-uploader";
      description = "Group to run the service as";
    };

    environment = mkOption {
      type = types.attrsOf types.str;
      default = {};
      example = {
        IMMICH_API_URL = "https://immich.example.com";
        WATCH_DIRECTORIES = "/home/user/Downloads,/home/user/Photos";
        ARCHIVE_DIRECTORY = "/home/user/Pictures/Archived";
        LOG_LEVEL = "INFO";
      };
      description = "Environment variables for the service";
    };

    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      example = "/run/secrets/immich-auto-uploader-env";
      description = "Path to environment file containing sensitive variables like IMMICH_API_KEY";
    };
  };

  config = mkIf cfg.enable {
    # Create user and group
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      home = cfg.workingDirectory;
      createHome = true;
    };

    users.groups.${cfg.group} = {};

    # Create working directory and copy source files
    systemd.tmpfiles.rules = [
      "d ${cfg.workingDirectory} 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.workingDirectory}/src 0755 ${cfg.user} ${cfg.group} -"
    ];

    # Systemd service definition
    systemd.services.immich-auto-uploader = {
      description = "Immich Auto-Uploader - Monitor directories and upload to Immich";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];

      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.workingDirectory;
        ExecStart = serviceScript;
        Restart = "always";
        RestartSec = "10s";
        
        # Security hardening
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = "read-only";
        ReadWritePaths = [ cfg.workingDirectory ];
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        RestrictSUIDSGID = true;
        RestrictRealtime = true;
        RestrictNamespaces = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        SystemCallFilter = [ "@system-service" "~@privileged @resources" ];
        SystemCallErrorNumber = "EPERM";
      };

      environment = cfg.environment;
      
      # Load sensitive environment variables from file
      serviceConfig.EnvironmentFile = mkIf (cfg.environmentFile != null) cfg.environmentFile;
    };

    # Ensure Python and dependencies are available
    environment.systemPackages = [ pythonEnv ];
  };
}