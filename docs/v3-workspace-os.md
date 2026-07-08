# Synzept V3 Workspace Operating System

Synzept V3 turns the product from separate AI tools into one workspace organized around the user's work: missions, projects, knowledge, conversations, and agents.

## Information Architecture

- Home: current mission, today's focus, active agents, pending approvals, recent knowledge, opportunities, open loops, and daily brief.
- Missions: outcome-centered goals and progress.
- Knowledge: memories, notes, files, decisions, and principles.
- Projects: active project state, tasks, blockers, and next steps.
- Agents: active AI agents, status, activity, plans, and approval requests.
- Daily OS: daily brief, focus, open loops, and routines.
- Search: global search across conversations, memories, projects, tasks, files, decisions, people, and missions.
- Settings: account, preferences, privacy, billing, and data controls.

## Folder Structure

- `backend/app/api/workspace_os.py`: mock Workspace OS API.
- `backend/app/schemas/workspace_os.py`: response and request contracts.
- `backend/app/services/workspace_os/`: mock data and service logic.
- `backend/tests/test_workspace_os.py`: backend contract tests.
- `src/lib/workspace-os/`: frontend types and mock data.
- `src/components/workspace-os/`: component library for home, search, and command bar.
- `src/app/(os)/search/page.tsx`: global search example.
- `src/app/(os)/agents/page.tsx`: agent workspace example.
- `frontend/app/dashboard-page.tsx`: routes the authenticated dashboard to Workspace Home.

## Component Library

- `WorkspaceHome`: unified first screen.
- `WorkspaceSearch`: instant global search with filters.
- `CommandBar`: universal command surface available from the shell.
- Existing shared UI primitives: `Card`, `Button`, `Badge`, `Input`, `PageFrame`, and the persistent `WorkspaceShell`.

## Mock APIs

- `GET /api/internal/workspace-os`
  Returns the full Workspace OS snapshot.
- `GET /api/internal/workspace-os/search?q=&filters=`
  Searches mock workspace index.
- `GET /api/internal/workspace-os/commands`
  Returns universal command definitions.
- `POST /api/internal/workspace-os/commands/run`
  Queues a mock command. No production action is executed.

## Mock Data Boundary

The V3 implementation uses realistic mock data only. It does not read production conversations, memories, files, projects, tasks, agents, or user accounts. Meaningful actions remain non-executing mock commands until a permissioned production action layer is introduced.

## Design Principles

- Minimal interface.
- Fast performance.
- Context always visible.
- Consistent design system.
- Mobile-first responsiveness.

## Extension Rules

Every new feature should answer:

- What workspace object does this serve?
- What context should remain visible while using it?
- Does it contribute to global search?
- Does it expose commands?
- Does an agent need explicit approval before taking action?
