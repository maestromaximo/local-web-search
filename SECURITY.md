# Security Policy

## Supported Versions

Security fixes are provided for the latest published version of
`local-web-search`.

## Reporting a Vulnerability

Please report security issues privately by opening a GitHub security advisory
for this repository, or by contacting the maintainer directly if advisories are
not available to you. Do not open a public issue for suspected vulnerabilities.

Include:

- affected version or commit
- operating system and Python version
- reproduction steps
- impact and any known workaround

## Security Notes

Local Web Search talks to a SearXNG instance and fetches URLs with Crawl4AI.
Treat fetched content as untrusted input. Do not pass secrets in search queries
or fetch URLs, and do not expose the HTTP API on an untrusted network without
your own authentication and network controls.
