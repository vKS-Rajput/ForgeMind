# Changelog

All notable changes to ForgeMind will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-26

### Added

- Phase 0: Repository foundation and engineering standards
  - `src` layout with hexagonal architecture per bounded context
  - Five bounded contexts: Knowledge, Graph, Retrieval, Reasoning, API
  - Shared module: types, errors, logging (structlog), configuration (pydantic-settings)
  - Complete toolchain: uv, ruff, mypy (strict), pytest, pytest-archon
  - Architectural fitness tests enforcing hexagonal boundaries
  - Pre-commit hooks for automated quality checks
  - ADRs 0001-0007 documenting all architectural decisions
  - README, CONTRIBUTING, and onboarding documentation
  - Environment configuration with .env.example and .env.test
