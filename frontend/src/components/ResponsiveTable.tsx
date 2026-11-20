import React, { useId } from 'react';

export interface TableColumn<T> {
  key: string;
  label: string;
  isRowHeader?: boolean;
  align?: 'left' | 'right';
  render: (row: T) => React.ReactNode;
}

interface ResponsiveTableProps<T> {
  caption: string;
  columns: TableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  emptyMessage?: string;
}

export function ResponsiveTable<T>({
  caption,
  columns,
  rows,
  getRowKey,
  emptyMessage = 'No records found.',
}: ResponsiveTableProps<T>) {
  const captionId = useId();

  const labelVars: Record<string, string> = {};
  columns.forEach((col, index) => {
    if (index > 0) {
      labelVars[`--label-${index + 1}`] = JSON.stringify(col.label);
    }
  });

  if (rows.length === 0) {
    return (
      <div className="alert alert-info" role="status">
        <span>{emptyMessage}</span>
      </div>
    );
  }

  return (
    <div
      tabIndex={0}
      role="region"
      aria-labelledby={captionId}
      className="table-wrapper"
      style={labelVars as React.CSSProperties}
    >
      <table className="data-table">
        <caption id={captionId}>{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                style={col.align === 'right' ? { textAlign: 'right' } : undefined}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((col, idx) =>
                col.isRowHeader || idx === 0 ? (
                  <th key={col.key} scope="row">
                    {col.render(row)}
                  </th>
                ) : (
                  <td
                    key={col.key}
                    style={col.align === 'right' ? { textAlign: 'right' } : undefined}
                  >
                    {col.render(row)}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
