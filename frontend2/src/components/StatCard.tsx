type StatCardProps = {
  title: string;
  value: string;
  subtitle: string;
  icon: string;
};

function StatCard({
  title,
  value,
  subtitle,
  icon,
}: StatCardProps) {
  return (
    <div className="stat-card">

      <div className="stat-icon">
        {icon}
      </div>

      <div className="stat-info">

        <p className="stat-title">
          {title}
        </p>

        <h3>
          {value}
        </h3>

        <p className="stat-subtitle">
          {subtitle}
        </p>

      </div>

    </div>
  );
}

export default StatCard;