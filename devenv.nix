{ pkgs, config, ... }:

{
  # Enable dotenv support for loading environment variables from a .env file.
  dotenv.enable = true;

  # Use a complete, consistent LLVM 21 toolchain.
  stdenv = pkgs.llvmPackages_21.stdenv;

  packages = with pkgs; [
    # Git and repository management
    git
    git-lfs
    github-cli

    # Node and PNPM added directly via standard system package attributes
    nodejs_24
    pnpm

    # Checker tools
    shellcheck
    lychee # Markdown link checker: lychee --offline --include-fragments '*.md' 'docs/**/*.md'

    # Go programming language.
    go

    # Useful command-line utilities for searching, filtering, and viewing files.
    ripgrep
    fd
    fzf
    bat
    eza
    tree
    jq
    yq-go

    # Retrieve files from the internet.
    wget
    curl

    # Python tooling (version-agnostic CLIs; the interpreter comes from languages.python)
    uv
    ruff
    black
    mypy

    imagemagick

    # --- CAD, PCB and printing (versions as resolved from devenv.lock on 2026-11-22) ---
    # FreeCAD is NOT provided here (owner decision 2026-11-23): devenv's patched nixpkgs
    # has no cached FreeCAD/VTK build, so the shell would compile both from source (hours).
    # Use the system FreeCAD instead (FreeCADCmd 1.1.4 on the owner's NixOS, checked
    # 2026-11-23); scripts print the FreeCAD version they ran with.
    kicad         # 10.0.8 with symbol/footprint/3D libraries; kicad-cli runs ERC/DRC and exports.
    # kikit is omitted: in this nixpkgs it depends on pybars3, which is marked insecure
    # (CVE-2026-119716). kicad-cli covers Gerber/drill/BOM/position exports.
    # gerbv is omitted: it depends on gtk2, which this nixpkgs marks broken.
    # Use KiCad's own Gerber viewer (gerbview) for Gerber/drill review.
    blender       # 5.2.3; renders and visual fit checks.
    bambu-studio  # 02.08.00.50; slicer for the Bambu Lab printer (X2D support still to verify).
                  # Unfree in nixpkgs; permitted individually in devenv.yaml.

    # --- ZMK / Zephyr firmware builds (nice!nano, nRF52840) ---
    # Zephyr is built with the GNU Arm Embedded toolchain via ZEPHYR_TOOLCHAIN_VARIANT=gnuarmemb
    # (see env below) because nixpkgs has no Zephyr SDK. Compatibility with the pinned ZMK
    # release is unverified until a first build succeeds.
    gcc-arm-embedded  # 15.3.rel2
    cmake
    ninja
    dtc
    gperf
    ccache
    protobuf      # protoc, used by ZMK Studio's nanopb RPC when enabled
    tio           # serial console for USB logging from the boards
    usbutils      # lsusb, to check enumeration of the dongle
  ];

  env = {
    ZEPHYR_TOOLCHAIN_VARIANT = "gnuarmemb";
    GNUARMEMB_TOOLCHAIN_PATH = "${pkgs.gcc-arm-embedded}";
  };

  delta.enable = true;

  languages.python = {
    enable = true;
    package = pkgs.python314.withPackages (ps: [
      ps.numpy
      ps.pillow
      ps.pytest
      ps.ipython

      # Zephyr/ZMK build requirements (west manages the ZMK and Zephyr checkouts).
      ps.west
      ps.pyelftools
      ps.pyyaml
      ps.pykwalify
      ps.packaging
      ps.intelhex
      ps.jsonschema
      ps.anytree
      ps.canopen
      ps.progress
      ps.psutil
      ps.pyserial
      ps.semver
      ps.tqdm
      ps.requests
      ps.protobuf
      ps.grpcio-tools

      # Layout source, geometry and export checks (keyboard project).
      ps.ezdxf       # read/write the baseplate DXF
      ps.shapely     # 2D plate/outline geometry checks
      ps.trimesh     # STL/3MF inspection and interference checks
      ps.scipy
      ps.matplotlib  # layout plots
      ps.jinja2      # generating KiCad/ZMK files from the layout source
    ]);
  };
    
  enterShell = ''
    if [ -d .git ]; then
      echo "Checking Git LFS initialization..."
      git lfs install --local --force
    else
      echo "Not a Git repository. Skipping Git LFS setup."
    fi

    echo "  pnpm: $(pnpm --version)"

    # Correctly register Context7 MCP via local stdio transport
    if [ -n "''${CONTEXT7_API_KEY:-}" ]; then
      echo "🔄 Registering Context7 MCP Server (stdio mode) in Pi Agent..."
      pi mcp add context7 --exposure direct \
        --env "CONTEXT7_API_KEY=$CONTEXT7_API_KEY" \
        -- npx -y @upstash/context7-mcp 2>/dev/null || true
    else
      echo "⚠️ Warning: CONTEXT7_API_KEY is not set. Check your .env file."
    fi

    if [ ! -f ".config/wt.toml" ]; then
      echo "💡 Run 'wt config create --project' to link this repo."
    fi

    # Only inside a worktrunk session: outside one the command has nothing to copy and
    # a non-zero exit would abort shell entry, which CI relies on for devenv -c.
    if [ -n "''${WT_SESSION:-}" ]; then
      wt step copy-ignored
    fi
  '';
}
