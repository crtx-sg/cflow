/**
 * Project detail page with proposals list.
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../services/api';
import { GenerateProposalsWizard } from '../components/GenerateProposalsWizard';

interface Project {
  id: number;
  name: string;
  local_path: string;
  compliance_standard: string;
  created_at: string;
  updated_at: string;
}

interface Proposal {
  id: number;
  name: string;
  project_id: number;
  author_id: number;
  status: 'draft' | 'review' | 'ready' | 'merged';
  created_at: string;
  updated_at: string;
}

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  review: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-green-100 text-green-800',
  merged: 'bg-blue-100 text-blue-800',
};

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isGenerateWizardOpen, setIsGenerateWizardOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`),
    enabled: !!projectId,
  });

  const { data: proposals, isLoading: proposalsLoading } = useQuery<Proposal[]>({
    queryKey: ['proposals', projectId, statusFilter],
    queryFn: () =>
      api.get(`/proposals/projects/${projectId}/proposals`, {
        status_filter: statusFilter || undefined,
      }),
    enabled: !!projectId,
  });

  if (projectLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900">Project not found</h3>
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="flex mb-6" aria-label="Breadcrumb">
        <ol className="flex items-center space-x-2">
          <li>
            <Link to="/projects" className="text-gray-500 hover:text-gray-700">
              Projects
            </Link>
          </li>
          <li className="text-gray-400">/</li>
          <li className="text-gray-900 font-medium">{project.name}</li>
        </ol>
      </nav>

      {/* Project header */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
            <p className="mt-1 text-sm text-gray-500">{project.local_path}</p>
          </div>
          <span className="px-3 py-1 text-sm font-medium rounded-full bg-green-100 text-green-800">
            {project.compliance_standard.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Proposals section */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900">Change Proposals</h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm border border-gray-300 rounded-md px-3 py-1"
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="review">Review</option>
            <option value="ready">Ready</option>
            <option value="merged">Merged</option>
          </select>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsGenerateWizardOpen(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium"
          >
            Generate with AI
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            New Proposal
          </button>
        </div>
      </div>

      {proposalsLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      ) : proposals?.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">No proposals yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Create a new change proposal to get started.
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            Create Proposal
          </button>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden rounded-md">
          <ul className="divide-y divide-gray-200">
            {proposals?.map((proposal) => (
              <li key={proposal.id}>
                <Link
                  to={`/proposals/${proposal.id}`}
                  className="block hover:bg-gray-50"
                >
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-blue-600 truncate">
                        {proposal.name}
                      </p>
                      <div className="ml-2 flex items-center space-x-2">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            statusColors[proposal.status]
                          }`}
                        >
                          {proposal.status.toUpperCase()}
                        </span>
                        <span className="text-sm text-gray-500">
                          {new Date(proposal.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isCreateModalOpen && (
        <CreateProposalModal
          projectId={project.id}
          onClose={() => setIsCreateModalOpen(false)}
        />
      )}

      {isGenerateWizardOpen && (
        <GenerateProposalsWizard
          projectId={project.id}
          onClose={() => setIsGenerateWizardOpen(false)}
          onComplete={() => {
            queryClient.invalidateQueries({ queryKey: ['proposals', projectId] });
            setIsGenerateWizardOpen(false);
          }}
        />
      )}
    </div>
  );
}

function CreateProposalModal({
  projectId,
  onClose,
}: {
  projectId: number;
  onClose: () => void;
}) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: { name: string }) =>
      api.post(`/proposals/projects/${projectId}/proposals`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposals', String(projectId)] });
      onClose();
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : 'Failed to create proposal');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ name });
  };

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Create New Proposal</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 p-3">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Proposal Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2"
              placeholder="add-user-authentication"
            />
            <p className="mt-1 text-xs text-gray-500">
              Use kebab-case (e.g., add-feature-name)
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
