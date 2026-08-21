# Sudo Command Handling

Never run `sudo` commands autonomously in a background task or terminal command.

Instead, always present the full `sudo` command to the user and ask them to run it manually in their own terminal. Briefly explain why (background tasks cannot handle interactive password prompts).

This applies to all `sudo` invocations including but not limited to:
- `sudo make install`
- `sudo apt install`
- `sudo cmake --install`
- `sudo cp`, `sudo rm`, `sudo chmod` on system paths
- Any command prefixed with `sudo`
