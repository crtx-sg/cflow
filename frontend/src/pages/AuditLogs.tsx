/**
 * Audit logs page (Admin only).
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiError } from '../services/api';

interface AuditLog {
  id: number;
  timestamp: string;
  user_id: number;
  action: string;
  resource_type: string;
  resource_id: number | null;
  old_value: string | null;
  new_value: string | null;
  ip_address: string | null;
}

interface AuditSummary {
  period_days: number;
  total_events: number;
  by_action: Record<string, number>;
  by_resource_type: Record<string, number>;
  top_users: { user_id: number; count: number }[];
}

export function AuditLogsPage() {
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');

  const { data: logs, isLoading, error } = useQuery<AuditLog[]>({
    queryKey: ['auditLogs', actionFilter, resourceTypeFilter],
    queryFn: () =>
      api.get('/audit', {
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
        limit: 100,
      }),
  });

  const { data: summary } = useQuery<AuditSummary>({
    queryKey: ['auditSummary'],
    queryFn: () => api.get('/audit/summary', { days: 7 }),
  });

  const { data: actions } = useQuery<string[]>({
    queryKey: ['auditActions'],
    queryFn: () => api.get('/audit/actions'),
  });

  const handleExport = async (format: 'csv' | 'json') => {
    const params = new URLSearchParams();
    params.append('format', format);
    if (actionFilter) params.append('action', actionFilter);
    if (resourceTypeFilter) params.append('resource_type', resourceTypeFilter);

    window.open(`/api/v1/audit/export?${params.toString()}`, '_blank');
  };

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="text-sm text-red-700">
          {error instanceof ApiError ? error.message : 'Failed to load audit logs'}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
        <div className="flex space-x-2">
          <button
            onClick={() => handleExport('csv')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white shadow rounded-lg p-4">
            <div className="text-sm text-gray-500">Total Events (7 days)</div>
            <div className="text-2xl font-bold text-gray-900">{summary.total_events}</div>
          </div>
          <div className="bg-white shadow rounded-lg p-4">
            <div className="text-sm text-gray-500">Action Types</div>
            <div className="text-2xl font-bold text-gray-900">
              {Object.keys(summary.by_action).length}
            </div>
          </div>
          <div className="bg-white shadow rounded-lg p-4">
            <div className="text-sm text-gray-500">Resource Types</div>
            <div className="text-2xl font-bold text-gray-900">
              {Object.keys(summary.by_resource_type).length}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="flex space-x-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All actions</option>
              {actions?.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resource Type</label>
            <select
              value={resourceTypeFilter}
              onChange={(e) => setResourceTypeFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">All types</option>
              <option value="project">Project</option>
              <option value="proposal">Proposal</option>
              <option value="comment">Comment</option>
              <option value="user">User</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : logs?.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">No audit logs found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your filters or check back later.
          </p>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs?.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    User #{log.user_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {log.resource_type}
                    {log.resource_id && ` #${log.resource_id}`}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                    {log.new_value && (
                      <span title={log.new_value}>
                        {log.new_value.substring(0, 50)}
                        {log.new_value.length > 50 && '...'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
