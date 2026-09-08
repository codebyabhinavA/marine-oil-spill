import type { Spill } from "../data/demoData";

type SatelliteEvidenceProps = {
  spill: Spill;
};

function SatelliteEvidence({ spill }: SatelliteEvidenceProps) {
  return (
    <section className="satellite-section">

      {/* SECTION HEADER */}
      <div className="section-header">
        <div>
          <p className="section-label">
            STEP 01 • SATELLITE INTELLIGENCE
          </p>

          <h2>
            Satellite Evidence
          </h2>

          <p>
            Satellite imagery analysis used to identify and confirm
            the detected oil spill.
          </p>
        </div>

        <div className="evidence-status">
          ● AI ANALYSIS COMPLETE
        </div>
      </div>


      {/* IMAGE COMPARISON */}
      <div className="satellite-grid">

        {/* BEFORE IMAGE */}
        <div className="satellite-card">

          <div className="satellite-card-header">
            <div>
              <h3>Before Detection</h3>
              <span>Reference satellite pass</span>
            </div>

            <span className="image-date">
              PREVIOUS PASS
            </span>
          </div>

          <div className="satellite-image before-image">

            <div className="satellite-ocean-pattern">
              <span>REFERENCE IMAGE</span>
            </div>

            <div className="scan-lines"></div>

            <div className="satellite-image-label">
              NO SIGNIFICANT OIL SIGNATURE
            </div>

          </div>

          <div className="image-info">

            <div>
              <span>Source</span>
              <strong>Satellite Archive</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>REFERENCE</strong>
            </div>

          </div>

        </div>


        {/* DETECTION IMAGE */}
        <div className="satellite-card">

          <div className="satellite-card-header">
            <div>
              <h3>Spill Detection</h3>
              <span>AI segmented imagery</span>
            </div>

            <span className="image-date">
              LATEST PASS
            </span>
          </div>

          <div className="satellite-image detection-image">

            <div className="satellite-ocean-pattern">
              <div className="spill-detection-shape"></div>
            </div>

            <div className="scan-lines"></div>

            <div className="detection-label">
              <span>AI DETECTED</span>
              <strong>OIL SPILL</strong>
            </div>

          </div>

          <div className="image-info">

            <div>
              <span>Detected Area</span>
              <strong>{spill.area}</strong>
            </div>

            <div>
              <span>Confidence</span>
              <strong>{spill.confidence}</strong>
            </div>

          </div>

        </div>

      </div>


      {/* ANALYSIS SUMMARY */}
      <div className="evidence-summary">

        <div className="summary-item">
          <span>Detection Model</span>
          <strong>
            Oil Spill Segmentation AI
          </strong>
        </div>

        <div className="summary-item">
          <span>Detected Coordinates</span>

          <strong>
            {spill.position[0].toFixed(2)}° N /{" "}
            {spill.position[1].toFixed(2)}° E
          </strong>
        </div>

        <div className="summary-item">
          <span>Detection Confidence</span>

          <strong className="confidence-value">
            {spill.confidence}
          </strong>
        </div>

        <div className="summary-item">
          <span>Analysis Status</span>

          <strong className="status-active">
            VERIFIED
          </strong>
        </div>

      </div>


      {/* FLOW CONNECTION */}
      <div className="analysis-flow-connector">
        <span>↓</span>
        <p>
          Spill confirmed → proceeding to incident location analysis
        </p>
      </div>

    </section>
  );
}

export default SatelliteEvidence;