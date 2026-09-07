# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

`modern-di-flask` is a Flask adapter over
[`modern-di`](https://github.com/modern-python/modern-di); [`CONTEXT.md`](CONTEXT.md) opens with
what it does and owns the vocabulary — read it before naming a concept in code, a test name, or an
issue title. Flask's own "app context" and "request context" are the easiest things to conflate
with modern-di's `Scope`; `CONTEXT.md` pins the difference. This is one of that project's
integrations, each of which lives in a separate repository and ships as a separate PyPI package.

## Commands

`just` (task runner) and `uv` (package manager). The [`justfile`](justfile) is the source of truth —
`just --list`, or read it. The one thing it does not say: a `ty` suppression is written
`# ty: ignore`, never `# type: ignore`.

## Architecture

All implementation is `modern_di_flask/main.py`, short enough to read whole. Read it.

## Workflow

Real work **not scheduled** becomes a GitHub issue.

Every link in `README.md` must be absolute: `https://github.com/modern-python/<repo>/blob/main/<path>`,
or `.../tree/main/<path>` for a directory. Never a relative path: `README.md` is also the PyPI long
description, and PyPI does not rewrite relative links, so a relative one 404s on the package page.

An invariant is a test whose name is the claim, with a docstring opening `INVARIANT:` and a second
paragraph naming **what breaks it** — design rationale, not a report of what this one test catches.
