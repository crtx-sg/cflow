# Capability: Project-Level AI Proposal Generation

## REMOVED Requirements

### Requirement: Proposal-level AI content generation

The proposal-level AI generation endpoint is removed as it is superseded by project-level generation.

#### Scenario: Proposal-level generate endpoint removed

- **Given** the existing `POST /api/v1/proposals/{id}/generate` endpoint
- **When** this change is implemented
- **Then** the endpoint is removed from the API
- **And** the "Generate with AI" button is removed from the ProposalDetail page
- **And** users must use project-level generation to create AI-generated proposals

## ADDED Requirements

### Requirement: Context analysis endpoint

The system SHALL provide an API endpoint to analyze detailed system context and suggest multiple change proposals.

#### Scenario: User submits detailed context for analysis

- **Given** the user is authenticated and has access to a project
- **When** the user sends a POST request to `/api/v1/projects/{project_id}/analyze-proposals` with detailed context including problem description, solution approach, users, authentication mechanisms, data flow, components, and tech stack
- **Then** the system analyzes the context using the configured LLM
- **And** the system returns a list of suggested proposals with kebab-case names, descriptions, and categories
- **And** the system returns an analysis summary

#### Scenario: Context is too short for meaningful analysis

- **Given** the user submits context with fewer than 100 characters
- **When** the analysis endpoint is called
- **Then** the system returns a 400 error indicating insufficient context

### Requirement: Batch proposal creation endpoint

The system SHALL provide an API endpoint to create multiple proposals from selected suggestions.

#### Scenario: User creates selected proposals

- **Given** the user has reviewed and selected proposals from the analysis suggestions
- **When** the user sends a POST request to `/api/v1/projects/{project_id}/create-proposals` with selected name/description pairs
- **Then** the system creates each proposal in DRAFT status
- **And** for each proposal, generates proposal.md, tasks.md, and spec delta content
- **And** the system returns list of created proposals with files_created

#### Scenario: Proposal name already exists

- **Given** a proposal with the same name already exists in the project
- **When** the user attempts to create a proposal with that name
- **Then** that proposal is marked as failed in the response
- **And** remaining proposals continue to be created

#### Scenario: Partial failure during batch creation

- **Given** the user selected multiple proposals for creation
- **When** one or more proposals fail to generate content
- **Then** the system continues processing remaining proposals
- **And** the response includes both created and failed proposals with error details

### Requirement: Multi-step wizard UI for proposal generation

The frontend SHALL provide a wizard interface for context input, suggestion review, and proposal creation.

#### Scenario: User enters detailed context

- **Given** the user is viewing the project detail page
- **When** the user clicks "Generate with AI" button
- **Then** a wizard modal opens with Step 1: Context Input
- **And** the user sees a large textarea with guidance for expected content types
- **And** the user can submit context by clicking "Analyze"

#### Scenario: User reviews and modifies suggestions

- **Given** the user has submitted context and received suggestions
- **When** the wizard displays Step 2: Review Suggestions
- **Then** the user sees suggestions as an editable list with checkboxes
- **And** the user can edit proposal names and descriptions
- **And** the user can add custom proposals or remove suggestions
- **And** the user can click "Analyze Again" to regenerate with modified context

#### Scenario: User creates selected proposals

- **Given** the user has selected one or more proposals
- **When** the user clicks "Create Selected"
- **Then** the wizard shows Step 3: Generation Progress
- **And** the user sees progress indicator for each proposal being created
- **And** on completion, the user sees summary with links to created proposals

### Requirement: Generated proposal structure

Each generated proposal SHALL include complete OpenSpec scaffolding.

#### Scenario: Proposal scaffold structure

- **Given** the user has created a proposal via the batch creation endpoint
- **When** the proposal content is generated
- **Then** the proposal includes proposal.md with Why, What Changes, and Impact sections
- **And** the proposal includes tasks.md with numbered implementation checklist
- **And** the proposal includes specs/{capability}/spec.md with Requirements and Scenarios
