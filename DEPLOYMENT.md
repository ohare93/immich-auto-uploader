# Deployment Guide for NixOS

This document provides comprehensive instructions for deploying the Immich Auto-Uploader on NixOS using various methods.

## Overview

The Immich Auto-Uploader can be deployed on NixOS in several ways:

1. **NixOS System Service** - System-wide service with security hardening
2. **User Service** - User-level service without root privileges  
3. **Home Manager** - Integrated with Home Manager configuration
4. **Nix Package** - Installable package for manual execution

## Prerequisites

- NixOS system
- Immich server running and accessible
- Immich API key (get from Immich web interface → Account Settings → API Keys)

## Method 1: NixOS System Service (Recommended for multi-user systems)

### Step 1: Add to NixOS Configuration

Add the service module to your `/etc/nixos/configuration.nix`:

```nix
{ config, pkgs, ... }:

{
  imports = [
    # ... your other imports
    /path/to/immich-auto-uploader/nixos-service.nix
  ];

  services.immich-auto-uploader = {
    enable = true;
    
    # Basic configuration
    environment = {
      IMMICH_API_URL = "https://your-immich-instance.com";
      WATCH_DIRECTORIES = "/home/user/Downloads,/home/user/Pictures/Import";
      ARCHIVE_DIRECTORY = "/home/user/Pictures/Archived";
      LOG_LEVEL = "INFO";
      FILE_STABILITY_WAIT_SECONDS = "5";
      FILE_STABILITY_CHECK_INTERVAL = "1.0";
    };
    
    # Secure way to provide API key
    environmentFile = "/run/secrets/immich-auto-uploader-env";
  };
}
```

### Step 2: Create Environment File

Create `/run/secrets/immich-auto-uploader-env`:

```bash
sudo mkdir -p /run/secrets
echo "IMMICH_API_KEY=your_api_key_here" | sudo tee /run/secrets/immich-auto-uploader-env
sudo chmod 600 /run/secrets/immich-auto-uploader-env
sudo chown immich-uploader:immich-uploader /run/secrets/immich-auto-uploader-env
```

### Step 3: Copy Source Files

```bash
sudo mkdir -p /var/lib/immich-auto-uploader/src
sudo cp -r src/* /var/lib/immich-auto-uploader/src/
sudo chown -R immich-uploader:immich-uploader /var/lib/immich-auto-uploader
```

### Step 4: Rebuild and Start

```bash
sudo nixos-rebuild switch
sudo systemctl status immich-auto-uploader
```

## Method 2: User Service

### Step 1: Import User Service Module

Add to your NixOS configuration or Home Manager:

```nix
{ config, pkgs, ... }:

{
  imports = [
    /path/to/immich-auto-uploader/user-service.nix
  ];

  services.immich-auto-uploader-user = {
    enable = true;
    sourceDirectory = "/home/user/immich-auto-uploader";
    
    environment = {
      IMMICH_API_URL = "https://your-immich-instance.com";
      WATCH_DIRECTORIES = "/home/user/Downloads";
      ARCHIVE_DIRECTORY = "/home/user/Pictures/Archived";
      LOG_LEVEL = "INFO";
    };
    
    environmentFile = "/home/user/.config/immich-auto-uploader/.env";
  };
}
```

### Step 2: Create Environment File

```bash
mkdir -p ~/.config/immich-auto-uploader
echo "IMMICH_API_KEY=your_api_key_here" > ~/.config/immich-auto-uploader/.env
chmod 600 ~/.config/immich-auto-uploader/.env
```

### Step 3: Start User Service

```bash
systemctl --user enable immich-auto-uploader
systemctl --user start immich-auto-uploader
systemctl --user status immich-auto-uploader
```

## Method 3: Home Manager Integration

### Step 1: Add to Home Manager Configuration

Add to your `home.nix`:

```nix
{ config, pkgs, ... }:

{
  imports = [
    /path/to/immich-auto-uploader/home-manager.nix
  ];

  services.immich-auto-uploader = {
    enable = true;
    
    # Configure non-sensitive settings
    settings = {
      IMMICH_API_URL = "https://your-immich-instance.com";
      WATCH_DIRECTORIES = "${config.home.homeDirectory}/Downloads,${config.home.homeDirectory}/Pictures/Import";
      ARCHIVE_DIRECTORY = "${config.home.homeDirectory}/Pictures/Archived";
      LOG_LEVEL = "INFO";
      FILE_STABILITY_WAIT_SECONDS = "5";
      MAX_FILE_SIZE_MB = "1000";
      WATCH_RECURSIVE = "true";
    };
    
    # Point to environment file for sensitive values
    environmentFile = "${config.home.homeDirectory}/.config/immich-auto-uploader/.env";
  };
}
```

### Step 2: Create Environment File

```bash
# Home Manager will create the config directory and example files
home-manager switch

# Copy and edit the environment file
cp ~/.config/immich-auto-uploader/.env.example ~/.config/immich-auto-uploader/.env
nano ~/.config/immich-auto-uploader/.env  # Edit with your API key
```

### Step 3: Apply Home Manager Configuration

```bash
home-manager switch
systemctl --user status immich-auto-uploader
```

### Home Manager Troubleshooting

**Environment File Issues:**
- Ensure the `.env` file exists at the specified path
- Check file permissions: `chmod 600 ~/.config/immich-auto-uploader/.env`
- Verify the file contains valid key=value pairs with no spaces around `=`
- Use absolute paths in `environmentFile` option

**Service Won't Start:**
```bash
# Check service status
systemctl --user status immich-auto-uploader

# View detailed logs
journalctl --user -u immich-auto-uploader -f

# Restart the service
systemctl --user restart immich-auto-uploader
```

**Configuration Options:**
- Use `settings` for non-sensitive configuration (visible in Nix store)
- Use `environmentFile` only for sensitive values like API keys
- Set `environmentFile = null` to disable environment file loading

## Method 4: Nix Package Installation

### Option A: Build and Install Locally

```bash
# Build the package
nix-build package.nix

# Install to user profile
nix-env -i ./result

# Or install system-wide
sudo nix-env -i ./result -p /nix/var/nix/profiles/system
```

### Option B: Using Flakes

Create a `flake.nix` file:

```nix
{
  description = "Immich Auto-Uploader";

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
        packages.default = immich-auto-uploader;
        
        apps.default = {
          type = "app";
          program = "${immich-auto-uploader}/bin/immich-auto-uploader";
        };
      }
    );
}
```

Then run:

```bash
# Build and run
nix run .

# Or install
nix profile install .

# Run manually
immich-auto-uploader
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMMICH_API_URL` | *required* | URL of your Immich instance |
| `IMMICH_API_KEY` | *required* | API key from Immich |
| `WATCH_DIRECTORIES` | `~/Downloads` | Comma-separated directories to monitor |
| `ARCHIVE_DIRECTORY` | `~/Pictures/Archived` | Directory to move processed files |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FILE_STABILITY_WAIT_SECONDS` | `5` | Seconds to wait for file size to stabilize |
| `FILE_STABILITY_CHECK_INTERVAL` | `1.0` | Seconds between file size checks |
| `MAX_FILE_SIZE_MB` | `1000` | Maximum file size in MB |
| `SUPPORTED_EXTENSIONS` | `jpg,jpeg,png,gif,bmp,tiff,webp,mp4,mov,avi,mkv,wmv,flv,m4v,3gp` | Supported file extensions |

## Service Management

### System Service Commands

```bash
# Check status
sudo systemctl status immich-auto-uploader

# Start/stop/restart
sudo systemctl start immich-auto-uploader
sudo systemctl stop immich-auto-uploader
sudo systemctl restart immich-auto-uploader

# View logs
sudo journalctl -u immich-auto-uploader -f

# Enable/disable auto-start
sudo systemctl enable immich-auto-uploader
sudo systemctl disable immich-auto-uploader
```

### User Service Commands

```bash
# Check status
systemctl --user status immich-auto-uploader

# Start/stop/restart
systemctl --user start immich-auto-uploader
systemctl --user stop immich-auto-uploader
systemctl --user restart immich-auto-uploader

# View logs
journalctl --user -u immich-auto-uploader -f

# Enable/disable auto-start
systemctl --user enable immich-auto-uploader
systemctl --user disable immich-auto-uploader
```

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check that source files are in the correct location
   - Verify environment file exists and has correct permissions
   - Check logs: `journalctl -u immich-auto-uploader -f`

2. **Permission denied errors**
   - Ensure directories are readable by the service user
   - For system service, check `/var/lib/immich-auto-uploader` permissions
   - For user service, check that paths are under user's home directory

3. **API connection failures**
   - Verify `IMMICH_API_URL` is correct and accessible
   - Check `IMMICH_API_KEY` is valid
   - Test with: `curl -H "x-api-key: YOUR_KEY" https://your-immich-instance.com/api/server-info`

4. **Files not being processed**
   - Check watch directories exist and are accessible
   - Verify file extensions are in `SUPPORTED_EXTENSIONS`
   - Check file sizes are under `MAX_FILE_SIZE_MB`
   - Enable DEBUG logging to see detailed processing info

### Debug Mode

Enable debug logging:

```bash
# For system service
sudo systemctl edit immich-auto-uploader
# Add: Environment="LOG_LEVEL=DEBUG"

# For user service  
systemctl --user edit immich-auto-uploader
# Add: Environment="LOG_LEVEL=DEBUG"

# Then restart and view logs
sudo systemctl restart immich-auto-uploader
journalctl -u immich-auto-uploader -f
```

### Log Locations

- System service: `journalctl -u immich-auto-uploader`
- User service: `journalctl --user -u immich-auto-uploader`
- Manual execution: Logs to console/terminal

## Security Considerations

### System Service Security

The system service includes several security hardening measures:

- Runs as dedicated `immich-uploader` user
- No new privileges allowed
- Private temporary directory
- Read-only access to most of the system
- Write access only to working directory
- System call filtering
- Memory protections

### File Permissions

- Environment files should be mode 600 (readable by owner only)
- API keys should never be stored in world-readable files
- Use `environmentFile` for sensitive configuration

### Network Security

- Ensure Immich server uses HTTPS in production
- Consider using a VPN or firewall to restrict access
- Regularly rotate API keys

## Advanced Configuration

### Multiple Upload Targets

To upload to multiple Immich instances, create separate service instances:

```nix
services.immich-auto-uploader-home = {
  enable = true;
  # ... configuration for home instance
};

services.immich-auto-uploader-remote = {
  enable = true;  
  # ... configuration for remote instance
};
```

### Custom File Processing

The service can be extended by modifying the Python source:

1. Add custom file validation in `src/config.py`
2. Extend metadata extraction in `src/file_processor.py`  
3. Add custom archiving logic in `src/file_processor.py`

### Performance Tuning

For high-volume environments:

- Increase `FILE_STABILITY_CHECK_INTERVAL` to reduce CPU usage
- Adjust `FILE_STABILITY_WAIT_SECONDS` based on typical download speeds
- Consider multiple instances for different directories
- Monitor system resources with `htop` or `systemd-cgtop`

## Migration from Other Systems

### From Docker

1. Export environment variables from Docker compose
2. Copy watch/archive directory mappings to NixOS paths
3. Update firewall rules if needed
4. Import existing processed file database if applicable

### From Systemd Service

1. Stop existing service: `sudo systemctl stop your-old-service`
2. Export configuration to NixOS format
3. Copy source files to NixOS-managed location
4. Remove old service files
5. Apply NixOS configuration

## Backup and Recovery

### Configuration Backup

Important files to backup:
- `/etc/nixos/configuration.nix` (NixOS config)
- `~/.config/nixpkgs/home.nix` (Home Manager config)
- Environment files (`.env` files)
- Archive directory contents

### Service State

The service maintains minimal state:
- Processed file tracking (in memory)
- Log files (via systemd journal)
- Archived files (in archive directory)

### Recovery Process

1. Restore NixOS/Home Manager configuration
2. Restore environment files with API keys
3. Restore archive directory if needed
4. Rebuild and restart services

## Development and Testing

### Running Tests

The project includes comprehensive unit tests covering all major functionality:

```bash
# Install test dependencies
pip install -r test-requirements.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
pytest tests/test_config.py -v                    # Config validation tests
pytest tests/test_file_watcher.py -v              # File watching tests  
pytest tests/test_file_processor.py -v            # File processing tests
pytest tests/test_immich_client.py -v             # API client tests

# Run tests matching a pattern
pytest -k "test_stability" -v                     # File stability tests
pytest -k "test_directory" -v                     # Directory handling tests
```

### Test Coverage

Tests cover:
- **Configuration validation** - Environment variables, directory checks, permissions
- **File watching** - Recursive/non-recursive, file stability detection, archive filtering
- **File processing** - Upload logic, archiving, duplicate detection, error handling
- **API client** - Connection testing, upload functionality, retry logic, MIME type detection
- **Directory handling** - Missing directories, permission issues, archive creation
- **Edge cases** - Large files, network failures, file conflicts, permission errors

### Development Workflow

```bash
# Set up development environment
python -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
pip install -r test-requirements.txt

# Run tests during development
make test-watch              # Auto-reload tests on changes
make test-coverage          # Generate coverage report
make lint                   # Check syntax
make clean                  # Clean test artifacts

# Before committing
make test-coverage          # Ensure good test coverage
make lint                   # Ensure no syntax errors
```

### Using with Nix/NixOS Development

```bash
# Enter development shell (includes Python + dependencies)
nix develop

# Run tests in Nix environment
nix develop -c pytest

# Check flake
nix flake check
```

This completes the comprehensive deployment guide for NixOS. Choose the method that best fits your use case and security requirements.