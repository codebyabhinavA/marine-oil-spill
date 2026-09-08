import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon,
  Polyline,
  Circle,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { useState } from "react";

import L from "leaflet";

import { spills, vessels } from "../data/demoData";

type MapViewProps = {
  onSpillSelect: (spillId: number) => void;
};


/* ============================= */
/* CUSTOM MAP ICONS */
/* ============================= */

const spillIcon = L.divIcon({
  className: "custom-map-icon",

  html: `
    <div class="map-emoji spill-emoji">
      🛢️
    </div>
  `,

  iconSize: [34, 34],
  iconAnchor: [17, 17],
  popupAnchor: [0, -18],
});


const originIcon = L.divIcon({
  className: "custom-map-icon",

  html: `
    <div class="map-emoji origin-emoji">
      📍
    </div>
  `,

  iconSize: [34, 34],
  iconAnchor: [17, 17],
  popupAnchor: [0, -18],
});


const vesselIcon = L.divIcon({
  className: "custom-map-icon",

  html: `
    <div class="map-emoji vessel-emoji">
      🚢
    </div>
  `,

  iconSize: [34, 34],
  iconAnchor: [17, 17],
  popupAnchor: [0, -18],
});


function MapView({
  onSpillSelect,
}: MapViewProps) {

  const [showSpills, setShowSpills] =
    useState(true);

  const [showVessels, setShowVessels] =
    useState(true);

  const [showDrift, setShowDrift] =
    useState(true);

  const [showRiskZones, setShowRiskZones] =
    useState(true);

  const [showOrigins, setShowOrigins] =
    useState(true);


  return (
    <div className="map-section">


      {/* ============================= */}
      {/* MAP HEADER */}
      {/* ============================= */}

      <div className="map-header">

        <div>

          <h2>
            Global Oil Spill Monitoring
          </h2>

          <p>
            Worldwide satellite monitoring and vessel activity
          </p>

        </div>


        {/* ============================= */}
        {/* LAYER MENU */}
        {/* ============================= */}

        <div className="layer-container">

          <button
            className="layer-button"
            onClick={() => {

              const menu =
                document.getElementById(
                  "layer-menu"
                );

              if (menu) {
                menu.classList.toggle("show");
              }

            }}
          >
            ⚙ Layers
          </button>


          <div
            id="layer-menu"
            className="layer-menu"
          >

            <label>

              <input
                type="checkbox"
                checked={showSpills}
                onChange={() =>
                  setShowSpills(
                    !showSpills
                  )
                }
              />

              🛢️ Oil Spills

            </label>


            <label>

              <input
                type="checkbox"
                checked={showVessels}
                onChange={() =>
                  setShowVessels(
                    !showVessels
                  )
                }
              />

              🚢 Vessels

            </label>


            <label>

              <input
                type="checkbox"
                checked={showDrift}
                onChange={() =>
                  setShowDrift(
                    !showDrift
                  )
                }
              />

              🌊 Drift Paths

            </label>


            <label>

              <input
                type="checkbox"
                checked={showRiskZones}
                onChange={() =>
                  setShowRiskZones(
                    !showRiskZones
                  )
                }
              />

              ⚠️ Risk Zones

            </label>


            <label>

              <input
                type="checkbox"
                checked={showOrigins}
                onChange={() =>
                  setShowOrigins(
                    !showOrigins
                  )
                }
              />

              📍 Estimated Origins

            </label>

          </div>

        </div>

      </div>


      {/* ============================= */}
      {/* MAP */}
      {/* ============================= */}

      <MapContainer
        center={[20, 0]}
        zoom={2}
        minZoom={2}
        className="map"
      >

        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />


        {/* ============================= */}
        {/* OIL SPILLS */}
        {/* ============================= */}

        {showSpills &&
          spills.map((spill) => (

            <div
              key={`spill-${spill.id}`}
            >

              {/* SPILL AREA */}

              <Polygon
                positions={spill.polygon}
                pathOptions={{
                  color: "red",
                  fillColor: "red",
                  fillOpacity: 0.35,
                  weight: 2,
                }}
              />


              {/* SPILL MARKER */}

              <Marker
                position={spill.position}
                icon={spillIcon}

                eventHandlers={{
                  click: () => {

                    /*
                     * Clicking the spill marker
                     * immediately selects the spill.
                     */

                    onSpillSelect(
                      spill.id
                    );

                  },
                }}
              >

                <Popup>

                  <div className="spill-popup">

                    <h3>
                      🛢️ {spill.name}
                    </h3>


                    <p>
                      <strong>
                        Spill Area:
                      </strong>{" "}
                      {spill.area}
                    </p>


                    <p>
                      <strong>
                        AI Confidence:
                      </strong>{" "}
                      {spill.confidence}
                    </p>


                    <p>
                      <strong>
                        Risk Level:
                      </strong>{" "}
                      {spill.risk}
                    </p>


                    <button
                      type="button"
                      className="investigate-button"

                      onClick={(event) => {

                        /*
                         * Prevent the button click
                         * from causing unwanted map
                         * event behaviour.
                         */

                        event.stopPropagation();

                        onSpillSelect(
                          spill.id
                        );

                      }}
                    >

                      🔍 Investigate Spill

                    </button>

                  </div>

                </Popup>

              </Marker>

            </div>

          ))}


        {/* ============================= */}
        {/* RISK ZONES */}
        {/* ============================= */}

        {showRiskZones &&
          spills.map((spill) => (

            <Polygon
              key={`risk-${spill.id}`}
              positions={spill.polygon}
              pathOptions={{
                color: "yellow",
                fillColor: "yellow",
                fillOpacity: 0.12,
                weight: 2,
                dashArray: "6 6",
              }}
            />

          ))}


        {/* ============================= */}
        {/* ESTIMATED ORIGINS */}
        {/* ============================= */}

        {showOrigins &&
          spills.map((spill) => (

            <div
              key={`origin-${spill.id}`}
            >

              <Circle
                center={spill.origin}
                radius={35000}
                pathOptions={{
                  color: "orange",
                  fillColor: "orange",
                  fillOpacity: 0.15,
                  weight: 2,
                  dashArray: "5 5",
                }}
              />


              <Marker
                position={spill.origin}
                icon={originIcon}
              >

                <Popup>

                  <div className="spill-popup">

                    <h3>
                      📍 Estimated Spill Origin
                    </h3>


                    <p>
                      <strong>
                        Latitude:
                      </strong>{" "}

                      {spill.origin[0].toFixed(2)}°
                    </p>


                    <p>
                      <strong>
                        Longitude:
                      </strong>{" "}

                      {spill.origin[1].toFixed(2)}°
                    </p>


                    <p>
                      Estimated using satellite,
                      drift and vessel correlation.
                    </p>


                    <strong>
                      DEMO ESTIMATE
                    </strong>

                  </div>

                </Popup>

              </Marker>

            </div>

          ))}


        {/* ============================= */}
        {/* DRIFT PATHS */}
        {/* ============================= */}

        {showDrift &&
          spills.map((spill) => (

            <Polyline
              key={`drift-${spill.id}`}
              positions={spill.drift}
              pathOptions={{
                color: "orange",
                weight: 3,
                dashArray: "8 8",
              }}
            />

          ))}


        {/* ============================= */}
        {/* VESSELS */}
        {/* ============================= */}

        {showVessels &&
          vessels.map((vessel) => (

            <Marker
              key={`vessel-${vessel.id}`}
              position={vessel.position}
              icon={vesselIcon}
            >

              <Popup>

                <h3>
                  🚢 {vessel.name}
                </h3>


                <p>
                  <strong>
                    Type:
                  </strong>{" "}
                  {vessel.type}
                </p>


                <p>
                  <strong>
                    Status:
                  </strong>{" "}
                  {vessel.status}
                </p>

              </Popup>

            </Marker>

          ))}


        {/* ============================= */}
        {/* MAP LEGEND */}
        {/* ============================= */}

        <div className="map-legend">

          <div className="legend-title">
            MAP LEGEND
          </div>


          <div className="legend-item">

            <span className="legend-symbol spill-symbol">
              🛢️
            </span>

            <span>
              Oil Spill
            </span>

          </div>


          <div className="legend-item">

            <span className="legend-symbol origin-symbol">
              📍
            </span>

            <span>
              Estimated Origin
            </span>

          </div>


          <div className="legend-item">

            <span className="legend-symbol risk-symbol">
              ▱
            </span>

            <span>
              Risk Zone
            </span>

          </div>


          <div className="legend-item">

            <span className="legend-symbol drift-symbol">
              ┄
            </span>

            <span>
              Predicted Drift
            </span>

          </div>


          <div className="legend-item">

            <span className="legend-symbol vessel-symbol">
              🚢
            </span>

            <span>
              Vessel
            </span>

          </div>

        </div>

      </MapContainer>

    </div>
  );
}

export default MapView;