# Privacy Policy

**Effective:** 2026-04-29
**Application:** Claude Launcher
**Publisher:** AXIA Enterprises

This privacy policy describes how Claude Launcher (the "Application") handles
information. It is written in plain language and is intentionally short, because
the Application's data practices are correspondingly minimal.

## Summary

The Application **does not collect, transmit, store, sell, or share any user
data**. There is no telemetry, no analytics, no crash reporting, no account
system, and no advertising. The Application is provided free of charge.

## What the Application does locally

The Application runs entirely on the user's own machine. It writes three small
files to the user's home directory to persist its UI state between launches:

| File | Contents |
|---|---|
| `~/.claude_launcher_favorites.json` | Folder paths the user has pinned |
| `~/.claude_launcher_state.json` | Recently opened folder paths and last window size |
| `~/.claude_launcher_bootstrapped` | Empty marker file indicating first-run setup completed |

These files are stored only on the user's machine. They are never read,
uploaded, or transmitted by the Application to any server. The user can
inspect or delete them at any time.

## Network activity

The Application itself initiates no network communication for analytics,
telemetry, update checks, or any other purpose.

The Application performs exactly two operations that may use the network, and
both are user-initiated invocations of standard third-party developer tools:

1. **First-run installation of the Claude CLI.** If the `claude` command is
   not already on the user's `PATH` at first launch, the Application invokes
   `npm install -g @anthropic-ai/claude-code` once. This contacts the public
   npm registry. The Application does not transmit identifying information
   beyond what `npm` itself sends as part of a standard package installation.
   This step is skipped on every subsequent launch.

2. **Clone Repo feature.** If the user clicks the Clone Repo button and
   supplies a Git URL, the Application invokes `git clone` against that URL.
   The Application does not store, log, or transmit the URL anywhere; it
   simply hands it to `git`.

In both cases, the Application is acting as a thin wrapper around tools the
user already has installed on their system, and is subject to those tools'
own privacy practices.

## The Claude CLI is a separate product

After the Application opens a terminal and starts the Claude CLI, the user is
interacting with a product made by Anthropic, not by AXIA Enterprises. The
Claude CLI communicates with Anthropic's servers as part of its normal
operation. That communication is governed by Anthropic's privacy policy, not
this one. AXIA Enterprises does not receive, observe, intercept, or store any
data exchanged between the Claude CLI and Anthropic.

## Children's privacy

The Application is not directed at children and does not knowingly collect
information from anyone, including children.

## Changes to this policy

If this policy changes in a material way, the change will be reflected in the
repository's commit history. The "Effective" date at the top of this file
indicates when the current version took effect.

## Contact

Questions about this policy or the Application can be raised by opening an
issue on the project's GitHub repository.

---

*Claude Launcher is built and provided by AXIA Enterprises and released under
the MIT license. The full source code is publicly available.*
