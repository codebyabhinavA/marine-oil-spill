import { useEffect, useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import MapView from "./components/MapView";
import StatCard from "./components/StatCard";
import SpillPanel from "./components/SpillPanel";

import { spills } from "./data/demoData";

function App() {
  const [selectedSpillId, setSelectedSpillId] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState("dashboard");

  const selectedSpill =
    spills.find((spill) => spill.id === selectedSpillId) || null;


  // =====================================================
  // SCROLL TO ANALYSIS AFTER A SPILL IS SELECTED
  // =====================================================

  useEffect(() => {
    if (selectedSpillId === null) {
      return;
    }

    const analysisSection =
      document.getElementById("spill-analysis");

    if (analysisSection) {
      setTimeout(() => {
        analysisSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    }
  }, [selectedSpillId]);


  // =====================================================
  // SIDEBAR NAVIGATION
  // =====================================================

  useEffect(() => {
    if (activeSection === "map") {
      document.getElementById("global-map")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }

    if (
      activeSection === "detection" ||
      activeSection === "vessels" ||
      activeSection === "analysis"
    ) {
      document.getElementById("spill-analysis")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [activeSection]);


  // =====================================================
  // SELECT SPILL
  // =====================================================

  const handleSpillSelect = (spillId: number) => {
    setSelectedSpillId(spillId);
    setActiveSection("analysis");
  };


  // =====================================================
  // CLOSE ANALYSIS
  // =====================================================

  const handleClosePanel = () => {
    setSelectedSpillId(null);
    setActiveSection("dashboard");
  };


  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="app">

      {/* SIDEBAR */}
      <Sidebar
        activeSection={activeSection}
        onSectionChange={setActiveSection}
      />


      {/* MAIN CONTENT */}
      <div className="content">

        <Header />

        <main className="main-content">


          {/* DASHBOARD HEADING */}
          <div className="dashboard-heading">

            <div>
              <p className="section-label">
                MARITIME INTELLIGENCE
              </p>

              <h2>
                Oil Spill Intelligence Dashboard
              </h2>

              <p>
                Monitor detected oil spills, ocean drift and
                vessel activity worldwide.
              </p>
            </div>

            <div className="demo-status">
              DEMO ENVIRONMENT
            </div>

          </div>


          {/* GLOBAL MAP */}
          <div id="global-map">

            <MapView
              onSpillSelect={handleSpillSelect}
            />

          </div>


          {/* STATISTICS */}
          <div className="stats-grid">

            <StatCard
              title="ACTIVE SPILLS"
              value="5"
              subtitle="Detected worldwide"
              icon="🛢️"
            />

            <StatCard
              title="SPILL AREA"
              value="96.7 km²"
              subtitle="Total detected area"
              icon="🌊"
            />

            <StatCard
              title="AI CONFIDENCE"
              value="92.6%"
              subtitle="Average detection confidence"
              icon="🎯"
            />

            <StatCard
              title="ACTIVE VESSELS"
              value="12"
              subtitle="Within analysis zones"
              icon="🚢"
            />

            <StatCard
              title="HIGH RISK"
              value="3"
              subtitle="Spills requiring attention"
              icon="⚠️"
            />

          </div>


          {/* =================================================
              SPILL ANALYSIS
          ================================================= */}

          <div
            id="spill-analysis"
            className="analysis-anchor"
          >

            {selectedSpill ? (

              <SpillPanel
                spill={selectedSpill}
                onClose={handleClosePanel}
              />

            ) : (

              <div className="empty-analysis">

                <div className="empty-analysis-icon">
                  🛰️
                </div>

                <h2>
                  Select a Spill to Investigate
                </h2>

                <p>
                  Select an oil-spill marker on the map to
                  open satellite evidence, vessel attribution,
                  drift analysis and response recommendations.
                </p>

              </div>

            )}

          </div>

        </main>

      </div>

    </div>
  );
}

export default App;