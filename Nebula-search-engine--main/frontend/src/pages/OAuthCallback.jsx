import { useEffect, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { saveTokens } from '../utils/storage';

export function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { api } = useAuth();
  const [error, setError] = useState(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const errorParam = searchParams.get('error');
    if (errorParam) {
      setError(decodeURIComponent(errorParam));
      return;
    }

    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (accessToken) {
      saveTokens({ access_token: accessToken, refresh_token: refreshToken || null });
      api.me()
        .then(() => navigate('/', { replace: true }))
        .catch(() => navigate('/?auth=1', { replace: true }));
    } else {
      setError('No authentication token received');
    }
  }, []);

  if (error) {
    return (
      <div className="oauth-callback-error">
        <h2>Authentication failed</h2>
        <p>{error}</p>
        <a href="/?auth=1" className="btn primary">Try again</a>
      </div>
    );
  }

  return (
    <div className="page-loading" aria-busy="true">
      <div className="skeleton-card" style={{ width: 240, margin: '4rem auto' }}>
        <p>Signing you in...</p>
      </div>
    </div>
  );
}
