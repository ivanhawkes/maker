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
  ];

  delta.enable = true;

  languages.python = {
    enable = true;
    package = pkgs.python314.withPackages (ps: [
      ps.numpy
      ps.pillow
      ps.pytest
      ps.ipython
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
