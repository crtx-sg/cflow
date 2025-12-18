# Design: add-project-level-ai-generation

## Context

This feature enables intelligent decomposition of complex system descriptions into multiple focused change proposals. The workflow involves two distinct phases: analysis (suggesting proposals) and creation (scaffolding selected proposals).

## User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Context Input                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Enter detailed description including:                     │  │
│  │  • Problem description                                     │  │
│  │  • Proposed solution approach                              │  │
│  │  • Users and their roles                                   │  │
│  │  • Authentication mechanisms                               │  │
│  │  • Data flow description                                   │  │
│  │  • System components breakdown                             │  │
│  │  • Tech stack considerations                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                        [Analyze]                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Review Suggestions                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ☑ add-user-authentication                                │    │
│  │   "Implement RBAC-based authentication for terminals"    │    │
│  │   [Edit] [Remove]                                        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ☑ add-data-encryption                                    │    │
│  │   "Add encryption for patient data at rest and transit"  │    │
│  │   [Edit] [Remove]                                        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ☐ add-audit-logging                                      │    │
│  │   "Implement comprehensive audit trail for compliance"   │    │
│  │   [Edit] [Remove]                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│  [+ Add Custom]                                                 │
│                    [Back]  [Analyze Again]  [Create Selected]   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Generation Progress                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ✓ add-user-authentication - Created                      │    │
│  │ ◐ add-data-encryption - Generating tasks.md...           │    │
│  │ ○ add-audit-logging - Pending                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│  Progress: 1/3 complete                                         │
└─────────────────────────────────────────────────────────────────┘
```

## API Design

### Analysis Endpoint

```
POST /api/v1/projects/{project_id}/analyze-proposals
Content-Type: application/json

{
  "context": "We are building a bedside patient monitoring system for ICU units.

    Problem: Currently, nurses must log into multiple systems to access patient
    vitals, medication schedules, and alert configurations.

    Proposed Solution: A unified terminal interface with role-based access.

    Users:
    - Nurses (view vitals, acknowledge alerts, update notes)
    - Physicians (full access, modify treatment plans)
    - Administrators (user management, system config)

    Authentication: Badge-based RFID + PIN, session timeout after 5 minutes

    Data Flow:
    - Vitals from medical devices via HL7 FHIR
    - Alerts pushed via WebSocket to active terminals
    - Notes synced to EMR system

    Components:
    - Terminal UI (React)
    - API Gateway (FastAPI)
    - Real-time alert service
    - HL7 FHIR adapter
    - User management service

    Tech Stack: Python, React, PostgreSQL, Redis, Docker"
}

Response:
{
  "suggestions": [
    {
      "name": "add-user-authentication",
      "description": "Implement RFID badge + PIN authentication with role-based access control for nurses, physicians, and administrators",
      "category": "security"
    },
    {
      "name": "add-vitals-integration",
      "description": "Create HL7 FHIR adapter to receive and normalize patient vitals from medical devices",
      "category": "integration"
    },
    {
      "name": "add-realtime-alerts",
      "description": "Implement WebSocket-based alert service for pushing notifications to active terminals",
      "category": "feature"
    },
    {
      "name": "add-emr-sync",
      "description": "Build synchronization service for patient notes to external EMR system",
      "category": "integration"
    }
  ],
  "analysis_summary": "Identified 4 proposals covering authentication, device integration, real-time features, and external system sync."
}
```

### Batch Creation Endpoint

```
POST /api/v1/projects/{project_id}/create-proposals
Content-Type: application/json

{
  "proposals": [
    {
      "name": "add-user-authentication",
      "description": "Implement RFID badge + PIN authentication with role-based access control"
    },
    {
      "name": "add-realtime-alerts",
      "description": "Implement WebSocket-based alert service for pushing notifications"
    }
  ],
  "original_context": "..." // Optional: include for richer generation
}

Response:
{
  "created": [
    {
      "id": 123,
      "name": "add-user-authentication",
      "status": "draft",
      "files_created": ["proposal.md", "tasks.md", "specs/user-auth/spec.md"]
    },
    {
      "id": 124,
      "name": "add-realtime-alerts",
      "status": "draft",
      "files_created": ["proposal.md", "tasks.md", "specs/realtime-alerts/spec.md"]
    }
  ],
  "failed": [],
  "total_tokens_used": 4500
}
```

## LLM Prompts

### Analysis Prompt

```
You are a software architect analyzing system requirements for compliance-critical software.

Given the detailed context below, identify distinct change proposals that should be
created separately. Each proposal should be:
- Focused on a single capability or concern
- Independently implementable and testable
- Named in kebab-case (e.g., add-user-authentication)

Context categories to consider:
- Authentication & Authorization
- Data integrations
- User interface components
- Backend services
- Security & compliance requirements

Return JSON:
{
  "suggestions": [
    {"name": "kebab-case-name", "description": "Brief description", "category": "category"}
  ],
  "analysis_summary": "Brief summary of analysis"
}
```

### Content Generation Prompt (per proposal)

```
Create an OpenSpec change proposal for: {description}

Project context: {compliance_standard}
Original system context: {original_context}

Generate:
1. proposal.md - Why, What Changes, Impact sections
2. tasks.md - Implementation checklist with numbered tasks
3. spec.md - Requirements with Scenarios in OpenSpec format

Format as JSON with keys: "proposal.md", "tasks.md", "spec.md"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GenerateProposalsWizard                                  │   │
│  │  ├── ContextInputStep                                     │   │
│  │  ├── ReviewSuggestionsStep                                │   │
│  │  └── GenerationStep                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend                                   │
│  ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │ projects.py      │    │ ProposalGeneratorService          │   │
│  │ ├─ /analyze-     │───▶│ ├─ analyze_context()              │   │
│  │ │   proposals    │    │ ├─ generate_proposal_content()    │   │
│  │ └─ /create-      │    │ └─ parse_llm_response()           │   │
│  │     proposals    │    └──────────────────────────────────┘   │
│  └──────────────────┘                    │                      │
│                                          ▼                      │
│                         ┌──────────────────────────────────┐    │
│                         │ LLM Provider (Ollama/OpenAI/etc) │    │
│                         └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two-phase workflow | Analyze → Create | Allows user review before committing resources |
| Editable suggestions | Yes | Users know their domain better than AI |
| Batch creation | Sequential with progress | Parallel would be faster but harder to debug |
| Spec delta generation | Include in batch | Complete scaffold in one operation |
| Original context passing | Optional in create | Enables richer generation if provided |

## File Structure (per created proposal)

```
openspec/changes/{proposal-name}/
├── proposal.md          # Why, What Changes, Impact
├── tasks.md             # Implementation checklist
├── design.md            # Optional, only for complex proposals
└── specs/
    └── {capability}/
        └── spec.md      # Requirements with Scenarios
```
