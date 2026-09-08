import type { Spill } from "../data/demoData";

type SpillTimelineProps = {
  spill: Spill;
};

function SpillTimeline({ spill }: SpillTimelineProps) {
  return (
    <div className="timeline-section">

      <div className="timeline-header">

        <div>
          <p className="section-label">
            TEMPORAL ANALYSIS
          </p>

          <h2>Spill Timeline</h2>

          <p>
            Estimated progression of the detected oil spill.
          </p>
        </div>

        <div className="timeline-status">
          ACTIVE EVENT
        </div>

      </div>

      <div className="timeline">

        <div className="timeline-item">

          <div className="timeline-marker">
            ✓
          </div>

          <div className="timeline-content">

            <div className="timeline-time">
              T - 48 HOURS
            </div>

            <h3>Possible Origin</h3>

            <p>
              No significant oil signature detected in
              reference satellite imagery.
            </p>

            <span className="timeline-tag">
              REFERENCE
            </span>

          </div>

        </div>

        <div className="timeline-item">

          <div className="timeline-marker">
            ✓
          </div>

          <div className="timeline-content">

            <div className="timeline-time">
              T - 24 HOURS
            </div>

            <h3>Initial Detection</h3>

            <p>
              Satellite analysis indicates the emergence
              of a possible surface oil anomaly.
            </p>

            <span className="timeline-tag">
              DETECTED
            </span>

          </div>

        </div>

        <div className="timeline-item active">

          <div className="timeline-marker">
            ●
          </div>

          <div className="timeline-content">

            <div className="timeline-time">
              CURRENT
            </div>

            <h3>Confirmed Spill</h3>

            <p>
              AI segmentation identifies an active oil spill
              covering approximately {spill.area}.
            </p>

            <span className="timeline-tag active-tag">
              ACTIVE
            </span>

          </div>

        </div>

        <div className="timeline-item predicted">

          <div className="timeline-marker">
            →
          </div>

          <div className="timeline-content">

            <div className="timeline-time">
              NEXT 24 HOURS
            </div>

            <h3>Predicted Movement</h3>

            <p>
              Drift modelling predicts continued movement
              along the estimated trajectory.
            </p>

            <span className="timeline-tag predicted-tag">
              PREDICTED
            </span>

          </div>

        </div>

      </div>

      <div className="timeline-summary">

        <div className="timeline-summary-item">
          <span>Estimated Duration</span>
          <strong>~24–48 hours</strong>
        </div>

        <div className="timeline-summary-item">
          <span>Current Status</span>
          <strong className="status-active">
            ACTIVE
          </strong>
        </div>

        <div className="timeline-summary-item">
          <span>AI Confidence</span>
          <strong>{spill.confidence}</strong>
        </div>

      </div>

    </div>
  );
}

export default SpillTimeline;