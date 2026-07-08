# Synzept V2 Skills Framework

## Overview

The Skills Framework turns capabilities into modular Skills that can gather context, reason over it, present a plan, and execute approved actions.

## SDK

- SkillRegistry manages registering and retrieving skills.
- Each skill exposes metadata and execution logic through a consistent interface.

## Mock skills

A complete set of mock skills is included for startup, productivity, knowledge, and personal workflows.

## Skill Library UI

The UI includes search, category filters, favorites, and recommended skills.

## APIs

- GET /api/internal/skills
- POST /api/internal/skills/execute

## Tests

- Backend test validates that the mock registry exposes the initial skill set.
