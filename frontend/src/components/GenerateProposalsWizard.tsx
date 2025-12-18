/**
 * Multi-step wizard for AI-assisted proposal generation.
 *
 * Step 1: Context Input - User enters detailed system description
 * Step 2: Review Suggestions - User reviews and modifies AI suggestions
 * Step 3: Generation - Create selected proposals with progress
 */

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api, ApiError } from '../services/api';

interface ProposalSuggestion {
  name: string;
  description: string;
  category: string;
  selected: boolean;
}

/**
 * Sanitize a name to valid kebab-case format.
 * - Converts to lowercase
 * - Replaces spaces and underscores with hyphens
 * - Removes invalid characters
 * - Ensures it starts with a letter and ends with letter/digit
 */
function toKebabCase(name: string): string {
  let result = name
    .toLowerCase()
    .trim()
    .replace(/[\s_]+/g, '-') // spaces and underscores to hyphens
    .replace(/[^a-z0-9-]/g, '') // remove invalid chars
    .replace(/-+/g, '-') // collapse multiple hyphens
    .replace(/^-+/, '') // remove leading hyphens
    .replace(/-+$/, ''); // remove trailing hyphens

  // Ensure starts with letter
  if (result && !/^[a-z]/.test(result)) {
    result = 'add-' + result;
  }

  // Ensure ends with letter or digit (not hyphen)
  if (result && !/[a-z0-9]$/.test(result)) {
    result = result.replace(/-+$/, '');
  }

  // Minimum length check
  if (result.length < 3) {
    result = result + '-feature';
  }

  return result;
}

interface CreatedProposal {
  id: number;
  name: string;
  status: string;
  files_created: string[];
}

interface FailedProposal {
  name: string;
  error: string;
}

interface GenerateProposalsWizardProps {
  projectId: number;
  onClose: () => void;
  onComplete: (createdIds: number[]) => void;
}

type WizardStep = 'context' | 'review' | 'generate';

export function GenerateProposalsWizard({
  projectId,
  onClose,
  onComplete,
}: GenerateProposalsWizardProps) {
  const [step, setStep] = useState<WizardStep>('context');
  const [context, setContext] = useState('');
  const [suggestions, setSuggestions] = useState<ProposalSuggestion[]>([]);
  const [analysisSummary, setAnalysisSummary] = useState('');
  const [error, setError] = useState('');
  const [createdProposals, setCreatedProposals] = useState<CreatedProposal[]>([]);
  const [failedProposals, setFailedProposals] = useState<FailedProposal[]>([]);

  // Analyze context mutation
  const analyzeMutation = useMutation({
    mutationFn: (ctx: string) =>
      api.post(`/projects/${projectId}/analyze-proposals`, { context: ctx }),
    onSuccess: (data: {
      suggestions: Array<{ name: string; description: string; category: string }>;
      analysis_summary: string;
    }) => {
      setSuggestions(
        data.suggestions.map((s) => ({
          ...s,
          // Sanitize AI-generated names to valid kebab-case
          name: toKebabCase(s.name),
          selected: true,
        }))
      );
      setAnalysisSummary(data.analysis_summary);
      setStep('review');
      setError('');
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : 'Failed to analyze context');
    },
  });

  // Create proposals mutation
  const createMutation = useMutation({
    mutationFn: (proposals: Array<{ name: string; description: string }>) =>
      api.post(`/projects/${projectId}/create-proposals`, {
        proposals,
        original_context: context,
      }),
    onSuccess: (data: {
      created: CreatedProposal[];
      failed: FailedProposal[];
    }) => {
      setCreatedProposals(data.created);
      setFailedProposals(data.failed);
      if (data.created.length > 0) {
        onComplete(data.created.map((p) => p.id));
      }
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : 'Failed to create proposals');
    },
  });

  const handleAnalyze = () => {
    if (context.trim().length < 100) {
      setError('Please provide at least 100 characters of context');
      return;
    }
    setError('');
    analyzeMutation.mutate(context);
  };

  const handleCreate = () => {
    const selected = suggestions.filter((s) => s.selected);
    if (selected.length === 0) {
      setError('Please select at least one proposal to create');
      return;
    }

    // Sanitize names to valid kebab-case format
    const proposalsToCreate = selected.map((s) => ({
      name: toKebabCase(s.name),
      description: s.description,
    }));

    // Check for duplicate names after sanitization
    const names = proposalsToCreate.map((p) => p.name);
    const uniqueNames = new Set(names);
    if (uniqueNames.size !== names.length) {
      setError('Some proposals have duplicate names after formatting. Please adjust the names.');
      return;
    }

    setError('');
    setStep('generate');
    createMutation.mutate(proposalsToCreate);
  };

  const toggleSelection = (index: number) => {
    setSuggestions((prev) =>
      prev.map((s, i) => (i === index ? { ...s, selected: !s.selected } : s))
    );
  };

  const updateSuggestion = (
    index: number,
    field: 'name' | 'description',
    value: string
  ) => {
    setSuggestions((prev) =>
      prev.map((s, i) => (i === index ? { ...s, [field]: value } : s))
    );
  };

  const removeSuggestion = (index: number) => {
    setSuggestions((prev) => prev.filter((_, i) => i !== index));
  };

  const addCustomProposal = () => {
    setSuggestions((prev) => [
      ...prev,
      {
        name: 'add-new-feature',
        description: 'Description of the new feature',
        category: 'custom',
        selected: true,
      },
    ]);
  };

  const selectedCount = suggestions.filter((s) => s.selected).length;

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">
              Generate Proposals with AI
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500"
            >
              <span className="sr-only">Close</span>
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Step indicator */}
          <div className="mt-4 flex items-center space-x-4">
            <div
              className={`flex items-center ${
                step === 'context' ? 'text-purple-600' : 'text-gray-400'
              }`}
            >
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'context'
                    ? 'bg-purple-100 text-purple-600'
                    : 'bg-gray-100'
                }`}
              >
                1
              </span>
              <span className="ml-2 text-sm font-medium">Context</span>
            </div>
            <div className="flex-1 h-px bg-gray-200" />
            <div
              className={`flex items-center ${
                step === 'review' ? 'text-purple-600' : 'text-gray-400'
              }`}
            >
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'review'
                    ? 'bg-purple-100 text-purple-600'
                    : 'bg-gray-100'
                }`}
              >
                2
              </span>
              <span className="ml-2 text-sm font-medium">Review</span>
            </div>
            <div className="flex-1 h-px bg-gray-200" />
            <div
              className={`flex items-center ${
                step === 'generate' ? 'text-purple-600' : 'text-gray-400'
              }`}
            >
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  step === 'generate'
                    ? 'bg-purple-100 text-purple-600'
                    : 'bg-gray-100'
                }`}
              >
                3
              </span>
              <span className="ml-2 text-sm font-medium">Generate</span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-3">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          {/* Step 1: Context Input */}
          {step === 'context' && (
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Describe your system in detail. Include:
              </p>
              <ul className="text-sm text-gray-500 mb-4 list-disc list-inside space-y-1">
                <li>Problem description - What issue are you solving?</li>
                <li>Proposed solution approach</li>
                <li>Users and their roles</li>
                <li>Authentication mechanisms</li>
                <li>Data flow description</li>
                <li>System components breakdown</li>
                <li>Tech stack considerations</li>
              </ul>
              <textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="We are building a bedside patient monitoring system for ICU units.

Problem: Currently, nurses must log into multiple systems...

Proposed Solution: A unified terminal interface with role-based access...

Users:
- Nurses (view vitals, acknowledge alerts)
- Physicians (full access, modify treatment plans)

Authentication: Badge-based RFID + PIN...

Data Flow:
- Vitals from medical devices via HL7 FHIR
- Alerts pushed via WebSocket

Components:
- Terminal UI (React)
- API Gateway (FastAPI)
- Real-time alert service

Tech Stack: Python, React, PostgreSQL"
                className="w-full h-64 p-3 border border-gray-300 rounded-md text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 font-mono"
              />
              <div className="mt-2 flex justify-between items-center">
                <span className="text-xs text-gray-500">
                  {context.length} characters (minimum 100)
                </span>
              </div>
            </div>
          )}

          {/* Step 2: Review Suggestions */}
          {step === 'review' && (
            <div>
              {analysisSummary && (
                <div className="mb-4 p-3 bg-purple-50 rounded-md">
                  <p className="text-sm text-purple-800">{analysisSummary}</p>
                </div>
              )}

              <div className="space-y-4">
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 ${
                      suggestion.selected
                        ? 'border-purple-300 bg-purple-50'
                        : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <input
                        type="checkbox"
                        checked={suggestion.selected}
                        onChange={() => toggleSelection(index)}
                        className="mt-1 h-4 w-4 text-purple-600 rounded border-gray-300 focus:ring-purple-500"
                      />
                      <div className="flex-1 space-y-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">
                            Name (kebab-case)
                          </label>
                          <input
                            type="text"
                            value={suggestion.name}
                            onChange={(e) =>
                              updateSuggestion(index, 'name', e.target.value)
                            }
                            onBlur={(e) => {
                              // Auto-fix name on blur
                              const sanitized = toKebabCase(e.target.value);
                              if (sanitized !== e.target.value) {
                                updateSuggestion(index, 'name', sanitized);
                              }
                            }}
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:border-purple-500 focus:ring-1 focus:ring-purple-500 font-mono"
                          />
                          {suggestion.name !== toKebabCase(suggestion.name) && (
                            <p className="mt-1 text-xs text-amber-600">
                              Will be formatted as: {toKebabCase(suggestion.name)}
                            </p>
                          )}
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">
                            Description
                          </label>
                          <textarea
                            value={suggestion.description}
                            onChange={(e) =>
                              updateSuggestion(index, 'description', e.target.value)
                            }
                            rows={2}
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                          />
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-gray-400">
                            Category: {suggestion.category}
                          </span>
                          <button
                            onClick={() => removeSuggestion(index)}
                            className="text-xs text-red-600 hover:text-red-800"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={addCustomProposal}
                className="mt-4 text-sm text-purple-600 hover:text-purple-800 flex items-center"
              >
                <svg
                  className="w-4 h-4 mr-1"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Add Custom Proposal
              </button>
            </div>
          )}

          {/* Step 3: Generation Progress */}
          {step === 'generate' && (
            <div>
              {createMutation.isPending && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
                  <p className="mt-4 text-sm text-gray-600">
                    Generating {selectedCount} proposal{selectedCount !== 1 ? 's' : ''}... This may take a moment.
                  </p>
                  <p className="mt-2 text-xs text-gray-400">
                    Each proposal requires AI content generation which can take 10-30 seconds.
                  </p>
                </div>
              )}

              {!createMutation.isPending && (
                <div className="space-y-4">
                  {/* Summary banner */}
                  {(createdProposals.length > 0 || failedProposals.length > 0) && (
                    <div
                      className={`p-4 rounded-md ${
                        failedProposals.length === 0
                          ? 'bg-green-50 border border-green-200'
                          : createdProposals.length === 0
                          ? 'bg-red-50 border border-red-200'
                          : 'bg-yellow-50 border border-yellow-200'
                      }`}
                    >
                      <p
                        className={`text-sm font-medium ${
                          failedProposals.length === 0
                            ? 'text-green-800'
                            : createdProposals.length === 0
                            ? 'text-red-800'
                            : 'text-yellow-800'
                        }`}
                      >
                        {failedProposals.length === 0
                          ? `All ${createdProposals.length} proposal(s) created successfully!`
                          : createdProposals.length === 0
                          ? `All ${failedProposals.length} proposal(s) failed to create.`
                          : `${createdProposals.length} created, ${failedProposals.length} failed.`}
                      </p>
                    </div>
                  )}

                  {createdProposals.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-green-800 mb-2">
                        Successfully Created ({createdProposals.length})
                      </h3>
                      <div className="space-y-2">
                        {createdProposals.map((p) => (
                          <div
                            key={p.id}
                            className="flex items-center justify-between p-3 bg-green-50 rounded-md border border-green-200"
                          >
                            <div>
                              <span className="font-medium text-green-900">
                                {p.name}
                              </span>
                              <span className="ml-2 text-xs text-green-600">
                                {p.files_created.join(', ')}
                              </span>
                            </div>
                            <a
                              href={`/proposals/${p.id}`}
                              className="text-sm text-green-700 hover:text-green-900"
                            >
                              View
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {failedProposals.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-red-800 mb-2">
                        Failed ({failedProposals.length})
                      </h3>
                      <div className="space-y-2">
                        {failedProposals.map((p, i) => (
                          <div
                            key={i}
                            className="p-3 bg-red-50 rounded-md border border-red-200"
                          >
                            <span className="font-medium text-red-900">
                              {p.name}
                            </span>
                            <p className="text-sm text-red-600 mt-1">{p.error}</p>
                          </div>
                        ))}
                      </div>
                      <p className="mt-3 text-xs text-gray-500">
                        Failed proposals may be due to name conflicts, invalid names, or LLM generation errors.
                        You can try creating them individually from the project page.
                      </p>
                    </div>
                  )}

                  {/* No results at all - complete failure */}
                  {createdProposals.length === 0 && failedProposals.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-sm text-gray-600">
                        No results received. This may indicate a server error.
                      </p>
                      <button
                        onClick={() => setStep('review')}
                        className="mt-4 text-sm text-purple-600 hover:text-purple-800"
                      >
                        Go back and try again
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <div>
            {step === 'review' && (
              <button
                onClick={() => setStep('context')}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Back
              </button>
            )}
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {step === 'generate' && !createMutation.isPending
                ? 'Close'
                : 'Cancel'}
            </button>

            {step === 'context' && (
              <button
                onClick={handleAnalyze}
                disabled={analyzeMutation.isPending || context.length < 100}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
              >
                {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze'}
              </button>
            )}

            {step === 'review' && (
              <>
                <button
                  onClick={() => {
                    analyzeMutation.mutate(context);
                  }}
                  disabled={analyzeMutation.isPending}
                  className="px-4 py-2 border border-purple-300 text-purple-700 rounded-md hover:bg-purple-50 text-sm font-medium disabled:opacity-50"
                >
                  Analyze Again
                </button>
                <button
                  onClick={handleCreate}
                  disabled={selectedCount === 0}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium disabled:opacity-50"
                >
                  Create Selected ({selectedCount})
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
