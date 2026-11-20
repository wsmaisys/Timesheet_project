import React from 'react';
import {
  CheckCircle2,
  Clock,
  FileEdit,
  PauseCircle,
  RotateCcw,
  XCircle,
} from 'lucide-react';

const LABEL_MAP: Record<string, string> = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  APPROVED: 'Approved',
  REJECTED: 'Returned',
  REOPENED: 'Reopened',
  CANCELLED: 'Cancelled',
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  ON_HOLD: 'On Hold',
  CLOSED: 'Closed',
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const label = LABEL_MAP[status] || status;
  const Icon =
    status === 'APPROVED' || status === 'ACTIVE'
      ? CheckCircle2
      : status === 'SUBMITTED'
        ? Clock
        : status === 'REJECTED' || status === 'CLOSED' || status === 'INACTIVE'
          ? XCircle
          : status === 'REOPENED'
            ? RotateCcw
            : status === 'ON_HOLD'
              ? PauseCircle
              : FileEdit;

  return (
    <span className={`status-badge status-${status}`}>
      <Icon size={13} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
};
