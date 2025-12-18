"""Service for AI-assisted proposal generation."""

import json
import logging
import re
from dataclasses import dataclass

from app.services.llm import get_llm_provider_for_project, LLMMessage, LLMProviderError

logger = logging.getLogger(__name__)


@dataclass
class ProposalSuggestion:
    """A suggested proposal from context analysis."""
    name: str
    description: str
    category: str


@dataclass
class AnalysisResult:
    """Result of context analysis."""
    success: bool
    suggestions: list[ProposalSuggestion]
    analysis_summary: str
    error: str | None = None
    tokens_used: int | None = None


@dataclass
class GeneratedContent:
    """Generated content for a proposal."""
    proposal_md: str
    tasks_md: str
    spec_md: str


@dataclass
class GenerationResult:
    """Result of content generation."""
    success: bool
    content: GeneratedContent | None = None
    error: str | None = None
    tokens_used: int | None = None


class ProposalGeneratorService:
    """Service for generating proposals from context using LLM."""

    # System prompt for context analysis
    ANALYSIS_SYSTEM_PROMPT = """You are a software architect analyzing system requirements for compliance-critical software development.

Given the detailed context below, identify distinct change proposals that should be created separately. Each proposal should be:
- Focused on a single capability or concern
- Independently implementable and testable
- Named in kebab-case (e.g., add-user-authentication)

Context categories to consider:
- Authentication & Authorization
- Data integrations
- User interface components
- Backend services
- Security & compliance requirements

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "suggestions": [
    {"name": "kebab-case-name", "description": "Brief description of the proposal", "category": "category"}
  ],
  "analysis_summary": "Brief summary of the analysis"
}"""

    # System prompt for content generation
    GENERATION_SYSTEM_PROMPT = """You are an AI assistant helping to create OpenSpec change proposals for compliance-critical software development.

Generate well-structured proposal content following OpenSpec conventions.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "proposal.md": "# Change: proposal-name\\n\\n## Why\\n\\nExplanation of why this change is needed.\\n\\n## What Changes\\n\\n### Component/Area\\n\\n- Change description\\n\\n## Impact\\n\\n- Impact description",
  "tasks.md": "# Tasks: proposal-name\\n\\n## 1. Section Name\\n\\n- [ ] 1.1 Task description\\n- [ ] 1.2 Task description",
  "spec.md": "# Capability: Capability Name\\n\\n## ADDED Requirements\\n\\n### Requirement: Requirement name\\n\\nThe system SHALL do something.\\n\\n#### Scenario: Scenario name\\n\\n- **Given** some precondition\\n- **When** some action\\n- **Then** some outcome"
}

Be concise but thorough. Follow OpenSpec conventions for requirement language (SHALL, MUST, etc.).
Use \\n for newlines in the JSON values."""

    def __init__(self, openspec_tool: str | None = None):
        """Initialize the service.

        Args:
            openspec_tool: The OpenSpec tool configured for the project (e.g., 'claude', 'cursor')
        """
        self._openspec_tool = openspec_tool

    def _get_llm_provider(self):
        """Get the LLM provider based on project configuration."""
        return get_llm_provider_for_project(self._openspec_tool)

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Extract JSON from LLM response, handling various formats."""
        # Clean the text
        clean_text = text.strip()

        logger.debug(f"Attempting to extract JSON from response (length={len(clean_text)})")

        # Try direct JSON parse first
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed: {e}")

        # Try to find JSON in markdown code block (greedy match for nested braces)
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', clean_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.debug(f"JSON in code block parse failed: {e}")

        # Try to find raw JSON object (greedy match)
        json_match = re.search(r'\{[\s\S]*\}', clean_text)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.debug(f"Raw JSON parse failed: {e}")
                # Try to fix common issues
                # 1. Replace actual newlines in string values with \n
                # 2. Remove control characters
                try:
                    # This is a hacky fix for LLMs that put actual newlines in JSON strings
                    fixed = re.sub(r'(?<!\\)\n', r'\\n', json_str)
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        logger.warning(f"Failed to extract JSON from response. First 500 chars: {clean_text[:500]}")
        return None

    @staticmethod
    def _extract_markdown_sections(text: str) -> dict | None:
        """Extract content from markdown format when LLM doesn't return JSON.

        Handles formats like:
        --- proposal.md ---
        content here
        --- tasks.md ---
        content here
        """
        result = {}

        # Try separator format: --- filename.md ---
        sections = re.split(r'---\s*([\w.]+)\s*---', text)
        if len(sections) > 2:
            # sections[0] is before first separator, then alternating name, content
            for i in range(1, len(sections) - 1, 2):
                filename = sections[i].strip()
                content = sections[i + 1].strip() if i + 1 < len(sections) else ""
                if filename and content:
                    result[filename] = content
            if result:
                logger.info(f"Extracted {len(result)} sections using separator format")
                return result

        # Try markdown header format: # proposal.md or ## proposal.md
        header_pattern = r'#+\s*(proposal\.md|tasks\.md|spec\.md)\s*\n([\s\S]*?)(?=#+\s*(?:proposal|tasks|spec)\.md|\Z)'
        matches = re.findall(header_pattern, text, re.IGNORECASE)
        if matches:
            for filename, content in matches:
                result[filename.lower()] = content.strip()
            if result:
                logger.info(f"Extracted {len(result)} sections using header format")
                return result

        return None

    @staticmethod
    def _clean_content(content: str) -> str:
        """Clean up content from LLM response."""
        # Replace escaped newlines with actual newlines
        clean = content.replace('\\n', '\n')

        # Remove markdown code block wrappers if present
        if clean.strip().startswith('```'):
            clean = re.sub(r'^```(?:json|markdown)?\s*\n?', '', clean.strip())
            clean = re.sub(r'\n?```\s*$', '', clean)

        return clean.strip()

    async def analyze_context(
        self,
        context: str,
        compliance_standard: str,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AnalysisResult:
        """Analyze detailed context and suggest proposals.

        Args:
            context: Detailed system context including problem, solution, users, etc.
            compliance_standard: The compliance standard (e.g., IEC_62304)
            model: Optional specific model to use
            temperature: LLM temperature for generation

        Returns:
            AnalysisResult with suggestions or error
        """
        if len(context.strip()) < 100:
            return AnalysisResult(
                success=False,
                suggestions=[],
                analysis_summary="",
                error="Context must be at least 100 characters for meaningful analysis",
            )

        llm_provider = self._get_llm_provider()

        user_message = f"""Analyze the following system context and suggest distinct change proposals.

Compliance Standard: {compliance_standard}

Context:
{context}

Return the suggestions as JSON."""

        messages = [
            LLMMessage(role="system", content=self.ANALYSIS_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_message),
        ]

        try:
            response = await llm_provider.generate(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=4096,
            )
        except LLMProviderError as e:
            return AnalysisResult(
                success=False,
                suggestions=[],
                analysis_summary="",
                error=f"LLM generation failed: {e}",
            )

        # Parse the response
        parsed = self._extract_json(response.content)
        if not parsed:
            return AnalysisResult(
                success=False,
                suggestions=[],
                analysis_summary="",
                error="Failed to parse LLM response as JSON",
                tokens_used=response.usage.total_tokens if response.usage else None,
            )

        # Extract suggestions
        suggestions = []
        for item in parsed.get("suggestions", []):
            if isinstance(item, dict) and "name" in item and "description" in item:
                suggestions.append(ProposalSuggestion(
                    name=item["name"],
                    description=item["description"],
                    category=item.get("category", "general"),
                ))

        return AnalysisResult(
            success=True,
            suggestions=suggestions,
            analysis_summary=parsed.get("analysis_summary", ""),
            tokens_used=response.usage.total_tokens if response.usage else None,
        )

    async def generate_proposal_content(
        self,
        name: str,
        description: str,
        compliance_standard: str,
        original_context: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Generate complete proposal content.

        Args:
            name: The proposal name (kebab-case)
            description: Brief description of the proposal
            compliance_standard: The compliance standard
            original_context: Optional original system context for richer generation
            model: Optional specific model to use
            temperature: LLM temperature for generation

        Returns:
            GenerationResult with content or error
        """
        llm_provider = self._get_llm_provider()

        context_section = ""
        if original_context:
            context_section = f"\n\nOriginal System Context:\n{original_context}"

        user_message = f"""Create an OpenSpec change proposal for: {description}

Proposal name: {name}
Compliance standard: {compliance_standard}
{context_section}

Generate the proposal content (proposal.md, tasks.md, spec.md) as JSON."""

        messages = [
            LLMMessage(role="system", content=self.GENERATION_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_message),
        ]

        try:
            logger.info(f"Generating content for proposal: {name}")
            response = await llm_provider.generate(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=4096,
            )
            logger.debug(f"LLM response received, length={len(response.content)}")
        except LLMProviderError as e:
            logger.error(f"LLM generation failed for {name}: {e}")
            return GenerationResult(
                success=False,
                error=f"LLM generation failed: {e}",
            )

        # Parse the response - try JSON first, then markdown sections
        parsed = self._extract_json(response.content)

        if not parsed:
            # Try extracting markdown sections as fallback
            logger.info(f"JSON parsing failed for {name}, trying markdown extraction")
            parsed = self._extract_markdown_sections(response.content)

        if not parsed:
            # Log the raw response for debugging
            logger.error(
                f"Failed to parse LLM response for {name}. "
                f"Response (first 1000 chars): {response.content[:1000]}"
            )
            # Instead of failing, use fallback content with a warning
            logger.warning(f"Using fallback content for {name}")
            parsed = {}  # Will trigger fallback content generation below

        # Extract content
        proposal_md = self._clean_content(parsed.get("proposal.md", ""))
        tasks_md = self._clean_content(parsed.get("tasks.md", ""))
        spec_md = self._clean_content(parsed.get("spec.md", ""))

        # Fallback to generating minimal content if parsing failed or fields are empty
        if not proposal_md:
            logger.debug(f"Using fallback for proposal.md: {name}")
            proposal_md = f"""# Change: {name}

## Why

{description}

## What Changes

This proposal implements the changes described above. Implementation details to be added.

## Impact

- Functional impact: Adds new capability as described
- Testing: Unit and integration tests required
"""
        if not tasks_md:
            logger.debug(f"Using fallback for tasks.md: {name}")
            tasks_md = f"""# Tasks: {name}

## 1. Analysis & Design

- [ ] 1.1 Review requirements and acceptance criteria
- [ ] 1.2 Design technical approach

## 2. Implementation

- [ ] 2.1 Implement core functionality
- [ ] 2.2 Add error handling and validation
- [ ] 2.3 Write unit tests

## 3. Testing & Documentation

- [ ] 3.1 Verify all acceptance criteria
- [ ] 3.2 Update documentation
"""
        if not spec_md:
            logger.debug(f"Using fallback for spec.md: {name}")
            # Convert name to capability name
            capability = name.replace("-", " ").title().replace(" ", "")
            spec_md = f"""# Capability: {capability}

## ADDED Requirements

### Requirement: {name.replace("-", " ").title()}

The system SHALL implement {description.lower()}.

#### Scenario: Basic functionality

- **Given** the system is operational
- **When** the feature is invoked
- **Then** the expected behavior occurs
"""

        return GenerationResult(
            success=True,
            content=GeneratedContent(
                proposal_md=proposal_md,
                tasks_md=tasks_md,
                spec_md=spec_md,
            ),
            tokens_used=response.usage.total_tokens if response.usage else None,
        )
