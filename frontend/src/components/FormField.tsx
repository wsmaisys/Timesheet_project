import React from 'react';

interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  errorText: string;
  children: (controlProps: {
    id: string;
    'aria-invalid': 'false';
    'aria-describedby'?: string;
    'data-error': string;
  }) => React.ReactNode;
}

export const FormField: React.FC<FormFieldProps> = ({ id, label, hint, errorText, children }) => {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = `${id}-error`;

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {hint ? (
        <span id={hintId} className="field-hint">
          {hint}
        </span>
      ) : null}
      {children({
        id,
        'aria-invalid': 'false',
        ...(hintId ? { 'aria-describedby': hintId } : {}),
        'data-error': errorId,
      })}
      <div id={errorId} className="error-msg">
        <span role="img" aria-label="Error">
          !
        </span>{' '}
        {errorText}
      </div>
    </div>
  );
};
