# Synzept V2 Skill Marketplace

## Overview

The Skill Marketplace lets users discover, install, enable, disable, and manage Skills from a mock catalog.

## Backend

- Service: SkillMarketplaceService
- Mock catalog: skill_marketplace_mock_data.py
- APIs:
  - GET /api/internal/skill-marketplace
  - GET /api/internal/skill-marketplace/installed
  - GET /api/internal/skill-marketplace/updates
  - POST /api/internal/skill-marketplace/install
  - GET /api/internal/skill-marketplace/developer-manifest/{skill_id}

## UI

- Marketplace home page with search, categories, featured skills, and catalog cards.
- Mock permissions and integrations are included in each skill.

## Developer SDK

- Skill manifests define metadata, permissions, integrations, and lifecycle hooks for third-party skills.

## Tests

- Backend test validates that the catalog exposes featured and installed skills.
