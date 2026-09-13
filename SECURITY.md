# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

---

## Security Architecture & Invariants

Clairvoy executes system-level filesystem operations (scanning, isolating duplicates, and hardlinking inodes). The core engine enforces strict safety boundaries:

1. **System Directory Blacklist**:
   Operations touching operating system root folders (e.g. `/`, `/bin`, `/sbin`, `/usr`, `/etc`, `C:\Windows`, `C:\Program Files`) are blocked by `clairvoy.core.security.resolve_safe_path`.
2. **Crash-Safe Atomic Hardlinking**:
   Hardlinking never unlinks an original file before linking. It creates a temporary link in the same parent directory and swaps it via atomic `os.replace`.
3. **Partition Boundary Integrity**:
   Hardlink creation verifies that candidate and keeper files share identical device IDs (`st_dev`) to prevent cross-filesystem partition link failures.
4. **Reversible Quarantine**:
   Quarantine operations record a cryptographic manifest (`quarantine_manifest.json`) enabling single-command rollback without data loss.

---

## Reporting a Vulnerability

If you discover a potential security vulnerability in Clairvoy, please report it privately:

- **Email**: `security@clairvoy.dev` (or open a private security advisory via GitHub)
- Please include steps to reproduce, impact assessment, and sample environment details.
- We will acknowledge receipt within 48 hours and work on a fix before public disclosure.
