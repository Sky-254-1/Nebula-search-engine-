import { forwardRef, useId } from 'react';

export const Input = forwardRef(function Input(
  { label, error, icon: Icon, className = '', ...props },
  ref
) {
  const id = useId();
  return (
    <div className={`input-group ${error ? 'input-error' : ''} ${className}`}>
      {label && <label htmlFor={id} className="input-label">{label}</label>}
      <div className="input-wrapper">
        {Icon && <Icon className="input-icon" aria-hidden="true" />}
        <input ref={ref} id={id} className="input-field" {...props} />
      </div>
      {error && <span className="input-error-text">{error}</span>}
    </div>
  );
});
