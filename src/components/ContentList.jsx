import ContentRow from "./ContentRow";
import EmptyState from "./EmptyState";

export default function ContentList({ items, totalCount }) {
  return (
    <section className="content-section">
      {/* Header count stays tied to the course total, not the filtered result length. */}
      <div className="content-section-header">
        <span className="eyebrow">Course content</span>
        <h3>{totalCount} Contents</h3>
      </div>

      <div className="content-list" role="list">
        {items.length > 0 ? (
          items.map((item) => <ContentRow key={item.id} item={item} />)
        ) : (
          <EmptyState
            compact
            title="No content matched your search"
            description="Try another lesson title or clear the search to view the full course outline."
          />
        )}
      </div>
    </section>
  );
}
