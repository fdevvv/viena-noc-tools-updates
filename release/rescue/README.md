# Legacy 1.3.25 rescue

This rescue is only for installations reporting:

- version: 1.3.25
- build: 1.3.25-release
- channel: RELEASE

It must not be used for 1.3.24 or for the bootstrap build.

The PowerShell script:
1. validates the source identity;
2. downloads the immutable bootstrap v3 package;
3. validates package SHA, file paths, sizes and per-file SHA;
4. creates a full sibling backup of the installation folder;
5. writes non-identity files first and build.json last;
6. verifies every target file;
7. restores the backup if an error occurs.

It does not touch Chrome storage. Keep the same extension folder/path so the unpacked extension identity/storage is preserved.

This is a one-time remediation for the historical incompatible 1.3.25 updater contract. Normal updates must use the bootstrap/modern channel architecture instead.
