# Security Notes

This repository should not contain private IP addresses, passwords, tokens, SSH keys, camera captures, or personal filesystem paths.

Before publishing changes, check:

```bash
git status
git diff --cached
```

Runtime captures such as `desktop-brain/latest_scene.jpg` and local model files are ignored by `.gitignore`.
