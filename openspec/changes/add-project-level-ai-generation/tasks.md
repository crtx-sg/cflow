# Tasks: add-project-level-ai-generation

## 1. Backend - Remove Proposal-Level Generation

- [x] 1.1 Remove `POST /proposals/{id}/generate` endpoint from `routers/proposals.py`
- [x] 1.2 Remove `GenerateProposalRequest` and `GenerateProposalResponse` schemas
- [x] 1.3 Remove related imports and LLM parsing helper functions
- [x] 1.4 Update API documentation to remove deprecated endpoint

## 2. Frontend - Remove Proposal-Level Generation UI

- [x] 2.1 Remove "Generate with AI" button from `ProposalDetail.tsx`
- [x] 2.2 Remove generate textarea, state variables, and related UI components
- [x] 2.3 Remove `generateMutation` and associated API calls
- [x] 2.4 Clean up any unused imports

## 3. Backend - Shared Services

- [x] 3.1 Create `ProposalGeneratorService` class in `services/proposal_generator.py`
- [x] 3.2 Implement `analyze_context()` method for decomposing context into suggestions
- [x] 3.3 Implement `generate_proposal_content()` method for creating proposal files
- [x] 3.4 Extract LLM prompt templates for analysis and content generation
- [x] 3.5 Implement response parsing with fallback handling

## 4. Backend - Analysis Endpoint

- [x] 4.1 Create `AnalyzeProposalsRequest` schema with fields: `context` (detailed description text)
- [x] 4.2 Create `ProposalSuggestion` schema with fields: `name`, `description`, `category`
- [x] 4.3 Create `AnalyzeProposalsResponse` schema with list of `ProposalSuggestion` and `analysis_summary`
- [x] 4.4 Implement `POST /projects/{project_id}/analyze-proposals` endpoint in `routers/projects.py`
- [x] 4.5 Add validation for minimum context length (100 characters)
- [x] 4.6 Design LLM prompt for decomposing detailed context into proposal suggestions
- [x] 4.7 Parse LLM response into structured ProposalSuggestion list

## 5. Backend - Batch Creation Endpoint

- [x] 5.1 Create `ProposalToCreate` schema with fields: `name`, `description`
- [x] 5.2 Create `CreateProposalsRequest` schema with list of `ProposalToCreate` and optional `original_context`
- [x] 5.3 Create `CreatedProposal` schema with `id`, `name`, `status`, `files_created`
- [x] 5.4 Create `CreateProposalsResponse` schema with `created`, `failed`, `total_tokens_used`
- [x] 5.5 Implement `POST /projects/{project_id}/create-proposals` endpoint
- [x] 5.6 For each selected proposal:
  - [x] 5.6.1 Validate name uniqueness and kebab-case format
  - [x] 5.6.2 Create proposal record in database with DRAFT status
  - [x] 5.6.3 Generate proposal.md content via LLM
  - [x] 5.6.4 Generate tasks.md content via LLM
  - [x] 5.6.5 Generate spec delta (specs/{capability}/spec.md) via LLM
  - [x] 5.6.6 Save all content via ContentVersioningService
- [x] 5.7 Handle partial failures (continue with remaining proposals)
- [x] 5.8 Add audit logging for batch proposal creation

## 6. Frontend - Context Input Step

- [x] 6.1 Create `GenerateProposalsWizard` component with step navigation state
- [x] 6.2 Create `ContextInputStep` component with:
  - [x] 6.2.1 Large textarea for detailed description
  - [x] 6.2.2 Guidance text/placeholders for expected content (problem, solution, users, auth, data flow, components, tech stack)
  - [x] 6.2.3 Character count indicator
- [x] 6.3 Add "Analyze" button to submit context for analysis
- [x] 6.4 Show loading state during analysis

## 7. Frontend - Review Suggestions Step

- [x] 7.1 Create `ReviewSuggestionsStep` component
- [x] 7.2 Display suggestions as editable card list:
  - [x] 7.2.1 Editable name input (with kebab-case validation)
  - [x] 7.2.2 Editable description textarea
  - [x] 7.2.3 Selection checkbox
  - [x] 7.2.4 Remove button per item
- [x] 7.3 Add "Add Custom Proposal" button for manual additions
- [x] 7.4 Add "Analyze Again" button to regenerate with modified context
- [x] 7.5 Show count of selected proposals
- [x] 7.6 Add "Back" button to return to context input step

## 8. Frontend - Generation Step

- [x] 8.1 Create `GenerationStep` component
- [x] 8.2 Show progress indicator with current proposal being generated
- [x] 8.3 Display success/failure status for each proposal
- [x] 8.4 On completion, show summary with links to created proposals
- [x] 8.5 Handle and display any failures with retry option

## 9. Frontend - Integration

- [x] 9.1 Add "Generate with AI" button (purple) to ProjectDetailPage header
- [x] 9.2 Open wizard modal on button click
- [x] 9.3 Refresh proposals list on wizard completion
- [ ] 9.4 Add keyboard shortcuts (Escape to close, Enter to proceed)

## 10. Testing

- [ ] 10.1 Unit tests for ProposalGeneratorService
- [ ] 10.2 Integration tests for analyze-proposals endpoint
- [ ] 10.3 Integration tests for create-proposals endpoint (including partial failures)
- [ ] 10.4 Frontend component tests for wizard steps
- [ ] 10.5 Verify proposal-level generate endpoint is removed
