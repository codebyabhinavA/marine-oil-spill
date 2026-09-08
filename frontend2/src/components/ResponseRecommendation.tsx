
import type { Spill } from "../data/demoData"; 
import { vessels } from "../data/demoData"; 
 
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
 
      {/* PANEL HEADER */} 
      <div className="spill-panel-header"> 
        <div> 
          <p className="panel-label"> 
            SPILL INVESTIGATION 
          </p> 
 
          <h2> 
            🛢️ {spill.name} 
          </h2> 
        </div> 
 
        <button 
          type="button" 
          className="close-panel-button" 
          onClick={onClose} 
        > 
          ✕ 
        </button> 
      </div> 
 
 
      {/* DETECTION INFORMATION */} 
      <div className="panel-section"> 
        <h3>Detection Analysis</h3> 
 
        <div className="detail-grid"> 
 
          <div className="detail-item"> 
            <span>Spill Area</span> 
            <strong>{spill.area}</strong> 
          </div> 
 
          <div className="detail-item"> 
            <span>AI Confidence</span> 
            <strong>{spill.confidence}</strong> 
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
 
 
      {/* SPILL LOCATION */} 
      <div className="panel-section"> 
        <h3>📍 Spill Location</h3> 
 
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
 
 
      {/* ESTIMATED ORIGIN */} 
      <div className="panel-section"> 
        <h3>📌 Estimated Spill Origin</h3> 
 
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
 
 
      {/* PREDICTED DRIFT */} 
      <div className="panel-section"> 
        <h3>🌊 Predicted Drift</h3> 
 
        <div className="drift-box"> 
 
          <p> 
            Current trajectory based on the detected 
            spill movement. 
          </p> 
 
          <strong> 
            → Drift path available 
          </strong> 
 
        </div> 
      </div> 
 
 
      {/* VESSEL ATTRIBUTION */} 
      <VesselAttribution 
        vessels={vessels} 
      /> 
 
 
      {/* SPILL TIMELINE */} 
      <SpillTimeline 
        spill={spill} 
      /> 
 
 
      {/* RISK ASSESSMENT */} 
      <RiskAssessment 
        spill={spill} 
      /> 
 
 
      {/* RESPONSE RECOMMENDATIONS */} 
      <ResponseRecommendation 
        spill={spill} 
      /> 
 
    </div> 
  ); 
} 
 
export default SpillPanel;   correct code

