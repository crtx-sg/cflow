/**
 * Proposal detail page with content editing and review.
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../services/api';

interface Proposal {
  id: number;
  name: string;
  project_id: number;
  author_id: number;
  status: 'draft' | 'review' | 'ready' | 'merged';
  created_at: string;
  updated_at: string;
}

interface Project {
  id: number;
  name: string;
  compliance_standard: string;
}

interface ProposalFile {
  path: string;
  content: string;
}

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  review: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-green-100 text-green-800',
  merged: 'bg-blue-100 text-blue-800',
};

export function ProposalDetailPage() {
  const { proposalId } = useParams<{ proposalId: string }>();
  const [selectedFile, setSelectedFile] = useState<string>('proposal.md');
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [actionError, setActionError] = useState('');
  const queryClient = useQueryClient();

  const { data: proposal, isLoading: proposalLoading } = useQuery<Proposal>({
    queryKey: ['proposal', proposalId],
    queryFn: () => api.get(`/proposals/${proposalId}`),
    enabled: !!proposalId,
  });

  const { data: project } = useQuery<Project>({
    queryKey: ['project', proposal?.project_id],
    queryFn: () => api.get(`/projects/${proposal?.project_id}`),
    enabled: !!proposal?.project_id,
  });

  const { data: fileContent, isLoading: fileLoading } = useQuery<ProposalFile>({
    queryKey: ['proposalFile', proposalId, selectedFile],
    queryFn: () => api.get(`/proposals/${proposalId}/content/${selectedFile}`),
    enabled: !!proposalId && !!selectedFile,
  });

  const updateFileMutation = useMutation({
    mutationFn: (data: { content: string; change_reason: string }) =>
      api.put(`/proposals/${proposalId}/content/${selectedFile}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposalFile', proposalId, selectedFile] });
      setIsEditing(false);
      setActionError('');
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : 'Failed to save');
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/proposals/${proposalId}/submit`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['proposal', proposalId] });
      setActionError('');
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : 'Failed to submit');
    },
  });

  const validateMutation = useMutation({
    mutationFn: () => api.post(`/proposals/${proposalId}/validate-draft`),
    onSuccess: () => {
      setActionError('');
      alert('Validation passed!');
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : 'Validation failed');
    },
  });

  if (proposalLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900">Proposal not found</h3>
        <Link to="/projects" className="mt-4 text-blue-600 hover:underline">
          Back to projects
        </Link>
      </div>
    );
  }

  const handleSave = () => {
    updateFileMutation.mutate({
      content: editContent,
      change_reason: 'Updated via UI',
    });
  };

  const handleStartEdit = () => {
    setEditContent(fileContent?.content || '');
    setIsEditing(true);
  };

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
          <li>
            <Link
              to={`/projects/${proposal.project_id}`}
              className="text-gray-500 hover:text-gray-700"
            >
              {project?.name || 'Project'}
            </Link>
          </li>
          <li className="text-gray-400">/</li>
          <li className="text-gray-900 font-medium">{proposal.name}</li>
        </ol>
      </nav>

      {/* Proposal header */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{proposal.name}</h1>
            <p className="mt-1 text-sm text-gray-500">
              Created {new Date(proposal.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <span
              className={`px-3 py-1 text-sm font-medium rounded-full ${statusColors[proposal.status]}`}
            >
              {proposal.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="mt-4 flex space-x-3">
          {proposal.status === 'draft' && (
            <>
              <button
                onClick={() => validateMutation.mutate()}
                disabled={validateMutation.isPending}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {validateMutation.isPending ? 'Validating...' : 'Validate'}
              </button>
              <button
                onClick={() => submitMutation.mutate()}
                disabled={submitMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
              >
                {submitMutation.isPending ? 'Submitting...' : 'Submit for Review'}
              </button>
            </>
          )}
        </div>

        {actionError && (
          <div className="mt-4 rounded-md bg-red-50 p-3">
            <div className="text-sm text-red-700">{actionError}</div>
          </div>
        )}
      </div>

      {/* File tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {['proposal.md', 'design.md', 'tasks.md'].map((file) => (
              <button
                key={file}
                onClick={() => {
                  setSelectedFile(file);
                  setIsEditing(false);
                }}
                className={`px-4 py-3 text-sm font-medium border-b-2 ${
                  selectedFile === file
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {file}
              </button>
            ))}
          </nav>
        </div>

        {/* File content */}
        <div className="p-6">
          {fileLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            </div>
          ) : isEditing ? (
            <div>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-96 font-mono text-sm border border-gray-300 rounded-md p-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
              <div className="mt-4 flex justify-end space-x-3">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={updateFileMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
                >
                  {updateFileMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex justify-end mb-4">
                {proposal.status === 'draft' && (
                  <button
                    onClick={handleStartEdit}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Edit
                  </button>
                )}
              </div>
              <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-md overflow-auto max-h-96">
                {fileContent?.content || 'No content yet'}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
