export default function StatsCardGroup({ progress }) {
  // These cards mirror the summary boxes from the sketch.
  const cards = [
    { label: "Content", value: progress.totalCount },
    { label: "Completed", value: progress.completedCount },
    { label: "Incomplete", value: progress.incompleteCount },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card) => (
        <article className="stat-card" key={card.label}>
          <span className="stat-value">{card.value}</span>
          <span className="stat-label">{card.label}</span>
        </article>
      ))}
    </div>
  );
}
