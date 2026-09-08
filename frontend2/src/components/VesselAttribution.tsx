import type { Vessel } from "../data/demoData";

type Attribution = {
  vesselId: number;
  distanceScore: number;
  timeScore: number;
  trajectoryScore: number;
  behaviourScore: number;
};

type VesselAttributionProps = {
  vessels: Vessel[];
};

const attributionData: Attribution[] = [
  {
    vesselId: 1,
    distanceScore: 92,
    timeScore: 88,
    trajectoryScore: 94,
    behaviourScore: 85,
  },
  {
    vesselId: 2,
    distanceScore: 65,
    timeScore: 61,
    trajectoryScore: 67,
    behaviourScore: 56,
  },
  {
    vesselId: 3,
    distanceScore: 38,
    timeScore: 32,
    trajectoryScore: 29,
    behaviourScore: 27,
  },
  {
    vesselId: 4,
    distanceScore: 24,
    timeScore: 19,
    trajectoryScore: 35,
    behaviourScore: 20,
  },
];

function calculateScore(data: Attribution) {
  return (
    data.distanceScore * 0.25 +
    data.timeScore * 0.25 +
    data.trajectoryScore * 0.3 +
    data.behaviourScore * 0.2
  );
}

function VesselAttribution({
  vessels,
}: VesselAttributionProps) {
  const rankings = attributionData
    .map((data) => {
      const vessel = vessels.find(
        (item) => item.id === data.vesselId
      );

      return {
        ...data,
        vessel,
        finalScore: calculateScore(data),
      };
    })
    .filter((item) => item.vessel)
    .sort((a, b) => b.finalScore - a.finalScore);

  return (
    <div className="attribution-section">

      <div className="attribution-header">

        <div>
          <p className="section-label">
            SOURCE ANALYSIS
          </p>

          <h2>Candidate Vessel Attribution</h2>

          <p>
            Vessel candidates ranked using AIS
            correlation and spill evidence.
          </p>
        </div>

        <div className="attribution-badge">
          ANALYSIS READY
        </div>

      </div>

      <div className="candidate-list">

        {rankings.map((candidate, index) => {

          const vessel = candidate.vessel!;

          return (
            <div
              className="candidate-card"
              key={vessel.id}
            >

              <div className="candidate-rank">
                {index === 0
                  ? "🥇"
                  : index === 1
                  ? "🥈"
                  : index === 2
                  ? "🥉"
                  : `#${index + 1}`}
              </div>

              <div className="candidate-info">

                <h3>
                  🚢 {vessel.name}
                </h3>

                <span>
                  {vessel.type} • {vessel.status}
                </span>

              </div>

              <div className="candidate-score">

                <span>
                  Attribution Score
                </span>

                <strong>
                  {candidate.finalScore.toFixed(1)}
                </strong>

              </div>

            </div>
          );
        })}

      </div>

      {rankings.length > 0 && (
        <div className="evidence-section">

          <h3>Attribution Evidence</h3>

          <div className="evidence-grid">

            <div className="evidence-card">
              <span>Distance</span>

              <div className="evidence-value">
                <strong>
                  {rankings[0].distanceScore}
                </strong>

                <span className="evidence-check">
                  ✓
                </span>
              </div>
            </div>

            <div className="evidence-card">
              <span>Time Match</span>

              <div className="evidence-value">
                <strong>
                  {rankings[0].timeScore}
                </strong>

                <span className="evidence-check">
                  ✓
                </span>
              </div>
            </div>

            <div className="evidence-card">
              <span>Trajectory</span>

              <div className="evidence-value">
                <strong>
                  {rankings[0].trajectoryScore}
                </strong>

                <span className="evidence-check">
                  ✓
                </span>
              </div>
            </div>

            <div className="evidence-card">
              <span>Behaviour</span>

              <div className="evidence-value">
                <strong>
                  {rankings[0].behaviourScore}
                </strong>

                <span className="evidence-check">
                  ✓
                </span>
              </div>
            </div>

          </div>

        </div>
      )}

      <div className="attribution-note">

        <strong>
          ⚠️ Candidate analysis only
        </strong>

        <span>
          Attribution scores indicate correlation
          between vessel activity and spill evidence.
          They do not establish responsibility or guilt.
        </span>

      </div>

    </div>
  );
}

export default VesselAttribution;