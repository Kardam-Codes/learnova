import ContentRow from "./ContentRow";

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
          // Empty state helps when the title-only search returns no matches.
          <div className="content-empty">
            No content matched your search. Try a different title.
          </div>
        )}
      </div>
    </section>
  );
}
