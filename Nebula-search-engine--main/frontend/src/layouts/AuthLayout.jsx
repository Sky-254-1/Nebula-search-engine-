import { Link } from 'react-router-dom';

export function AuthLayout({ children, title }) {
  return (
    <div className="auth-layout">
      <div className="auth-container">
        <Link to="/" className="auth-logo">Nebula</Link>
        {title && <h1 className="auth-title">{title}</h1>}
        {children}
      </div>
    </div>
  );
}

export default AuthLayout;
