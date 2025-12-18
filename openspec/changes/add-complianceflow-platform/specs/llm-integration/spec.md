# LLM Integration

## ADDED Requirements

### Requirement: Provider-Agnostic Interface

The system SHALL abstract LLM calls behind a provider-agnostic interface.

#### Scenario: OpenAI provider

- **WHEN** configuration specifies provider "openai"
- **THEN** the system uses OpenAI API for completions

#### Scenario: Anthropic provider

- **WHEN** configuration specifies provider "anthropic"
- **THEN** the system uses Anthropic API for completions

#### Scenario: Ollama provider (local)

- **WHEN** configuration specifies provider "ollama"
- **THEN** the system uses local Ollama server for completions
- **AND** no API key is required

#### Scenario: vLLM provider (local)

- **WHEN** configuration specifies provider "vllm"
- **THEN** the system uses local vLLM server for completions
- **AND** no API key is required

### Requirement: LLM Configuration

The system SHALL support configurable LLM settings per project or system-wide.

#### Scenario: System-wide default configuration

- **WHEN** no project-specific LLM config exists
- **THEN** the system uses system-wide default configuration

#### Scenario: Project-specific configuration

- **WHEN** project has LLM configuration
- **THEN** the system uses project-specific settings

#### Scenario: Configuration includes model selection

- **WHEN** LLM is configured
- **THEN** configuration includes provider, model name, base_url (for local), temperature, max_tokens

### Requirement: Tool-to-LLM Provider Mapping

The system SHALL map OpenSpec tools to their corresponding LLM providers.

#### Scenario: Claude tool mapping

- **WHEN** project is configured with OpenSpec tool "claude"
- **THEN** the system uses Anthropic as the LLM provider for that project
- **AND** uses project-specific API key if configured, otherwise falls back to global

#### Scenario: Cursor/Copilot tool mapping

- **WHEN** project is configured with OpenSpec tool "cursor" or "github-copilot"
- **THEN** the system uses OpenAI as the LLM provider for that project

#### Scenario: Gemini tool mapping

- **WHEN** project is configured with OpenSpec tool "gemini"
- **THEN** the system uses Google AI as the LLM provider for that project

#### Scenario: Custom tool mapping

- **WHEN** project is configured with an unrecognized tool or "none"
- **THEN** the system uses the global default LLM provider

#### Scenario: Per-project API key override

- **WHEN** project has a `.env` file with provider-specific API key (e.g., `ANTHROPIC_API_KEY`)
- **THEN** the system uses that API key for LLM calls within that project
- **AND** the key takes precedence over global configuration

### Requirement: Fallback Chain

The system SHALL support fallback to secondary providers on failure.

#### Scenario: Primary provider fails

- **WHEN** primary LLM provider returns error
- **THEN** the system attempts secondary provider if configured
- **AND** logs the fallback event

#### Scenario: All providers fail

- **WHEN** all configured providers fail
- **THEN** the system returns 502 Bad Gateway
- **AND** includes error details from each provider attempt

#### Scenario: Fallback to local

- **WHEN** cloud providers are unavailable
- **AND** local provider (Ollama/vLLM) is configured as fallback
- **THEN** the system uses local provider

### Requirement: API Key Security

The system SHALL securely manage LLM provider API keys.

#### Scenario: API key from environment

- **WHEN** API key is configured via environment variable
- **THEN** the system reads key from environment
- **AND** never logs or exposes the key

#### Scenario: API key from encrypted storage

- **WHEN** API key is stored in database
- **THEN** the key is encrypted at rest
- **AND** decrypted only when making API calls

#### Scenario: API key validation

- **WHEN** a provider is configured
- **THEN** the system validates API key on startup
- **AND** logs warning if validation fails

### Requirement: Token Usage Tracking

The system SHALL track LLM token usage for cost management.

#### Scenario: Track completion usage

- **WHEN** an LLM completion is made
- **THEN** the system records prompt_tokens, completion_tokens, total_tokens
- **AND** associates usage with user and project

#### Scenario: Usage query endpoint

- **WHEN** an Admin calls `GET /api/v1/llm/usage`
- **THEN** the system returns usage statistics
- **AND** supports filtering by date range, user, project

#### Scenario: Usage alerts

- **WHEN** usage exceeds configured threshold
- **THEN** the system logs warning
- **AND** optionally notifies administrators

### Requirement: Streaming Completions

The system SHALL support streaming LLM responses for real-time feedback.

#### Scenario: Stream completion

- **WHEN** iteration is requested with streaming enabled
- **THEN** the system streams tokens as they are generated
- **AND** sends chunks via WebSocket

#### Scenario: Stream interruption

- **WHEN** WebSocket disconnects during streaming
- **THEN** the system cancels the LLM request
- **AND** does not write partial content to files

### Requirement: Meta-Prompt Construction

The system SHALL construct effective prompts for compliance document iteration.

#### Scenario: Prompt includes context

- **WHEN** constructing iteration prompt
- **THEN** the prompt includes: compliance standard context, current draft content, user instruction, selected review comments

#### Scenario: Prompt structure

- **WHEN** meta-prompt is constructed
- **THEN** it follows the template:
  ```
  CONTEXT: Safety Critical Update for {compliance_standard}
  CURRENT DRAFT: {file_content}
  USER INSTRUCTION: {user_instruction}
  REQUIRED FIXES:
  {formatted_comments}
  OUTPUT: Return the complete updated file content.
  ```

#### Scenario: Large file handling

- **WHEN** draft file exceeds context window
- **THEN** the system truncates with summary
- **AND** warns user about truncation
