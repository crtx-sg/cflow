# Change: add-project-level-ai-generation

## Why

Creating comprehensive compliance proposals for complex systems requires careful decomposition of requirements into manageable, traceable change proposals. Currently, users must manually:
1. Analyze their system requirements
2. Identify discrete change proposals
3. Create each proposal individually
4. Generate content for each

This is time-consuming and error-prone, especially for large system changes that span multiple components. Users need an AI-assisted workflow that can:
- Accept detailed system context (problem, solution, users, auth, data flow, components, tech stack)
- Intelligently decompose this into multiple focused change proposals
- Allow user review and modification of suggestions before creation
- Scaffold complete OpenSpec change structures for selected proposals

## What Changes

### Backend - Removals

1. **Remove proposal-level generate endpoint** - `DELETE /api/v1/proposals/{id}/generate`
   - This endpoint is superseded by project-level generation
   - Remove `GenerateProposalRequest` and `GenerateProposalResponse` schemas
   - Remove associated LLM prompt logic (will be refactored into shared service)

### Backend - Additions

1. **Analysis Endpoint** - `POST /api/v1/projects/{project_id}/analyze-proposals`
   - Accepts detailed context (problem, solution, users, auth mechanisms, data flow, components, tech stack)
   - Uses LLM to analyze and decompose into suggested proposals
   - Returns list of suggested proposals with names and descriptions
   - Does NOT create any proposals yet

2. **Batch Creation Endpoint** - `POST /api/v1/projects/{project_id}/create-proposals`
   - Accepts list of selected proposals (name + description pairs)
   - For each selected item, creates proposal and generates:
     - proposal.md
     - tasks.md
     - spec delta in specs/<capability>/spec.md
   - Scaffolds files in `openspec/changes/<proposal-name>/`
   - Returns list of created proposals

### Frontend - Removals

1. **Remove proposal-level "Generate with AI" UI** from ProposalDetail page
   - Remove generate button, textarea, and associated state
   - Remove `generateMutation` and related API calls

### Frontend - Additions

1. **Generate with AI Modal** - Multi-step wizard:
   - **Step 1: Context Input** - Large textarea for detailed description with guidance prompts:
     - Problem description
     - Proposed solution approach
     - Users and their roles
     - Authentication mechanisms
     - Data flow description
     - System components breakdown
     - Tech stack considerations
   - **Step 2: Review Suggestions** - Display AI-suggested proposals as editable list:
     - Each item shows: name (editable), description (editable), checkbox for selection
     - User can add/remove items
     - "Analyze Again" button to regenerate suggestions
   - **Step 3: Generation** - Create selected proposals with progress indicator

## Impact

- MUST support iterative refinement (user can go back to modify context)
- MUST allow user to edit AI suggestions before creation
- MUST scaffold complete OpenSpec structure including spec deltas
- SHALL handle partial failures gracefully (some proposals may fail to create)
- Performance: Analysis may take 15-30 seconds; batch creation scales with selection count
