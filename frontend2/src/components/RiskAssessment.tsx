import type { Spill } from "../data/demoData";

type RiskAssessmentProps = {
  spill: Spill;
};

function RiskAssessment({ spill }: RiskAssessmentProps) {
  const riskLevel = spill.risk;

  const riskDescription =
    riskLevel === "CRITICAL"
      ? "Immediate environmental and coastal impact possible."
      : riskLevel === "HIGH"
      ? "Significant environmental impact possible. Active monitoring recommended."
      : "Moderate environmental impact. Continue monitoring.";

  return (
    <div className="risk-assessment-section">

      {/* HEADER */}
      <div className="risk-assessment-header">

        <div>
          <p className="section-label">
            IMPACT ANALYSIS
          </p>

          <h2>Drift & Risk Assessment</h2>

          <p>
            Predicted spill movement and potential impact
            based on current intelligence.
          </p>
        </div>

        <div
          className={`risk-badge risk-${riskLevel.toLowerCase()}`}
        >
          {riskLevel} RISK
        </div>

      </div>

      {/* DRIFT INFORMATION */}
      <div className="risk-content">

        <div className="drift-analysis-card">

          <div className="risk-card-title">
            <span>🌊</span>
            <h3>Predicted Drift</h3>
          </div>

          <div className="drift-direction">

            <div className="drift-point current">
              <span>●</span>
              <strong>Current</strong>
              <small>
                {spill.position[0].toFixed(2)}°,{" "}
                {spill.position[1].toFixed(2)}°
              </small>
            </div>

            <div className="drift-arrow">
              ─────────→
            </div>

            <div className="drift-point predicted">
              <span>●</span>
              <strong>Predicted</strong>
              <small>
                {spill.drift[spill.drift.length - 1][0].toFixed(2)}°,
                {" "}
                {spill.drift[spill.drift.length - 1][1].toFixed(2)}°
              </small>
            </div>

          </div>

          <div className="drift-stats">

            <div>
              <span>Forecast Window</span>
              <strong>24 Hours</strong>
            </div>

            <div>
              <span>Trajectory Points</span>
              <strong>{spill.drift.length}</strong>
            </div>

            <div>
              <span>Model Status</span>
              <strong className="status-active">
                ACTIVE
              </strong>
            </div>

          </div>

        </div>

        {/* RISK CARD */}
        <div className="risk-analysis-card">

          <div className="risk-card-title">
            <span>⚠️</span>
            <h3>Environmental Risk</h3>
          </div>

          <div className="risk-meter">

            <div className="risk-meter-labels">
              <span>LOW</span>
              <span>MODERATE</span>
              <span>HIGH</span>
              <span>CRITICAL</span>
            </div>

            <div className="risk-meter-track">

              <div
                className={`risk-meter-fill risk-fill-${riskLevel.toLowerCase()}`}
              ></div>

              <div
                className={`risk-marker risk-marker-${riskLevel.toLowerCase()}`}
              ></div>

            </div>

          </div>

          <div className="risk-description">

            <strong>
              {riskLevel} Environmental Risk
            </strong>

            <p>
              {riskDescription}
            </p>

          </div>

        </div>

      </div>

      {/* IMPACT INDICATORS */}
      <div className="impact-indicators">

        <div className="impact-card">

          <span className="impact-icon">
            🐟
          </span>

          <div>
            <span>Marine Ecosystem</span>
            <strong>
              {riskLevel === "CRITICAL"
                ? "SEVERE"
                : riskLevel === "HIGH"
                ? "HIGH"
                : "MODERATE"}
            </strong>
          </div>

        </div>

        <div className="impact-card">

          <span className="impact-icon">
            🏖️
          </span>

          <div>
            <span>Coastal Exposure</span>
            <strong>
              {riskLevel === "CRITICAL"
                ? "HIGH"
                : riskLevel === "HIGH"
                ? "MODERATE"
                : "LOW"}
            </strong>
          </div>

        </div>

        <div className="impact-card">

          <span className="impact-icon">
            🚢
          </span>

          <div>
            <span>Navigation Risk</span>
            <strong>
              {riskLevel === "CRITICAL"
                ? "HIGH"
                : "MODERATE"}
            </strong>
          </div>

        </div>

      </div>

    </div>
  );
}

export default RiskAssessment;

