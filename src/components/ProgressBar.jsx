export default function ProgressBar({ percentage }) {
  // Chunked progress matches the visual direction from the design document.
  const chunkCount = 10;
  const filledChunks = Math.round((percentage / 100) * chunkCount);

  return (
    <div className="progress-bar" aria-label={`${percentage}% completed`}>
      {Array.from({ length: chunkCount }, (_, index) => (
        <span
          key={index}
          className={`progress-chunk ${index < filledChunks ? "is-filled" : ""}`}
        />
      ))}
    </div>
  );
}
