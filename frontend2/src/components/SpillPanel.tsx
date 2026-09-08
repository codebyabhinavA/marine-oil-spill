import type { Spill } from "../data/demoData";
import { vessels } from "../data/demoData";

import SatelliteEvidence from "./SatelliteEvidence";
import VesselAttribution from "./VesselAttribution";
import SpillTimeline from "./SpillTimeline";
import RiskAssessment from "./RiskAssessment";
import ResponseRecommendation from "./ResponseRecommendation";

type SpillPanelProps = {
  spill: Spill;
  onClose: () => void;
};

function SpillPanel({ spill, onClose }: SpillPanelProps) {
  return (
    <div className="spill-panel">

      {/* ================================================= */}
      {/* INVESTIGATION HEADER */}
      {/* ================================================= */}

      <div className="spill-panel-header">

        <div>
          <p className="panel-label">
            SPILL INVESTIGATION
          </p>

          <h2>
            🛢️ {spill.name}
          </h2>

          <p className="panel-subtitle">
            End-to-end incident intelligence analysis
          </p>
        </div>

        <button
          type="button"
          className="close-panel-button"
          onClick={onClose}
        >
          ✕
        </button>

      </div>


      {/* ================================================= */}
      {/* STEP 01 — SATELLITE EVIDENCE */}
      {/* ================================================= */}

      <SatelliteEvidence spill={spill} />


      {/* ================================================= */}
      {/* STEP 02 — DETECTION ANALYSIS */}
      {/* ================================================= */}

      <div className="panel-section">

        <div className="analysis-step-label">
          STEP 02 • INCIDENT DETECTION
        </div>

        <h3>
          Detection Analysis
        </h3>

        <div className="detail-grid">

          <div className="detail-item">
            <span>Spill Area</span>
            <strong>
              {spill.area}
            </strong>
          </div>

          <div className="detail-item">
            <span>AI Confidence</span>
            <strong>
              {spill.confidence}
            </strong>
          </div>

          <div className="detail-item">
            <span>Risk Level</span>
            <strong className="risk-high">
              {spill.risk}
            </strong>
          </div>

          <div className="detail-item">
            <span>Detection Status</span>
            <strong className="status-active">
              ACTIVE
            </strong>
          </div>

        </div>

      </div>


      {/* ================================================= */}
      {/* STEP 03 — INCIDENT LOCATION */}
      {/* ================================================= */}

      <div className="panel-section">

        <div className="analysis-step-label">
          STEP 03 • INCIDENT LOCATION
        </div>

        <h3>
          📍 Spill Location
        </h3>

        <div className="location-box">

          <p>
            <span>Latitude</span>

            <strong>
              {spill.position[0].toFixed(2)}°
            </strong>
          </p>

          <p>
            <span>Longitude</span>

            <strong>
              {spill.position[1].toFixed(2)}°
            </strong>
          </p>

        </div>

      </div>


      {/* ================================================= */}
      {/* STEP 04 — ORIGIN */}
      {/* ================================================= */}

      <div className="panel-section">

        <div className="analysis-step-label">
          STEP 04 • ORIGIN ESTIMATION
        </div>

        <h3>
          📌 Estimated Spill Origin
        </h3>

        <div className="location-box">

          <p>
            <span>Latitude</span>

            <strong>
              {spill.origin[0].toFixed(2)}°
            </strong>
          </p>

          <p>
            <span>Longitude</span>

            <strong>
              {spill.origin[1].toFixed(2)}°
            </strong>
          </p>

        </div>

        <div className="origin-note">
          DEMO ESTIMATE — Derived from spill movement,
          drift trajectory and vessel correlation.
        </div>

      </div>


      {/* ================================================= */}
      {/* STEP 05 — DRIFT */}
      {/* ================================================= */}

      <div className="panel-section">

        <div className="analysis-step-label">
          STEP 05 • DRIFT PREDICTION
        </div>

        <h3>
          🌊 Predicted Drift
        </h3>

        <div className="drift-box">

          <p>
            Current trajectory based on detected spill
            movement and predicted ocean drift.
          </p>

          <strong>
            → Drift path available
          </strong>

        </div>

      </div>


      {/* ================================================= */}
      {/* STEP 06 — VESSEL ATTRIBUTION */}
      {/* ================================================= */}

      <div className="analysis-step-label">
        STEP 06 • VESSEL CORRELATION
      </div>

      <VesselAttribution
        vessels={vessels}
      />


      {/* ================================================= */}
      {/* STEP 07 — TIMELINE */}
      {/* ================================================= */}

      <div className="analysis-step-label">
        STEP 07 • INCIDENT TIMELINE
      </div>

      <SpillTimeline
        spill={spill}
      />


      {/* ================================================= */}
      {/* STEP 08 — RISK */}
      {/* ================================================= */}

      <div className="analysis-step-label">
        STEP 08 • RISK ASSESSMENT
      </div>

      <RiskAssessment
        spill={spill}
      />


      {/* ================================================= */}
      {/* STEP 09 — RESPONSE */}
      {/* ================================================= */}

      <div className="analysis-step-label">
        STEP 09 • RESPONSE
      </div>

      <ResponseRecommendation
        spill={spill}
      />


      {/* ================================================= */}
      {/* END OF INVESTIGATION */}
      {/* ================================================= */}

      <div className="investigation-complete">

        <div className="complete-icon">
          ✓
        </div>

        <h3>
          Investigation Flow Complete
        </h3>

        <p>
          Satellite evidence, incident location, origin,
          drift, vessel correlation, timeline, risk and
          response analysis have been reviewed.
        </p>

      </div>

    </div>
  );
}

export default SpillPanel;