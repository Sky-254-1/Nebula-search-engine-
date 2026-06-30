export function Skeleton({ width, height = 16, count = 1, className = '', ...props }) {
  if (count > 1) {
    return (
      <div className={`skeleton-group ${className}`} {...props}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className="skeleton" style={{ width, height }} />
        ))}
      </div>
    );
  }
  return <div className={`skeleton ${className}`} style={{ width, height }} {...props} />;
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`skeleton-card ${className}`}>
      <Skeleton height={20} width="60%" />
      <Skeleton height={14} width="100%" />
      <Skeleton height={14} width="80%" />
    </div>
  );
}
