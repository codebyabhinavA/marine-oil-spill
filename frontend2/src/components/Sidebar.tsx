type SidebarProps = {
  activeSection: string;
  onSectionChange: (section: string) => void;
};

function Sidebar({
  activeSection,
  onSectionChange,
}: SidebarProps) {
  const navigationItems = [
    {
      id: "dashboard",
      icon: "🏠",
      label: "Dashboard",
    },
    {
      id: "map",
      icon: "🗺️",
      label: "GIS Map",
    },
    {
      id: "detection",
      icon: "🛰️",
      label: "Spill Detection",
    },
    {
      id: "vessels",
      icon: "🚢",
      label: "Vessels",
    },
    {
      id: "analysis",
      icon: "📊",
      label: "Analysis",
    },
  ];

  return (
    <aside className="sidebar">

      {/* LOGO */}
      <div className="logo">
        🛢️ OILWATCH
      </div>

      {/* NAVIGATION */}
      <nav>
        {navigationItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`nav-item ${
              activeSection === item.id ? "active" : ""
            }`}
            onClick={() => onSectionChange(item.id)}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* BOTTOM */}
      <div className="sidebar-bottom">

        <button
          type="button"
          className={`nav-item ${
            activeSection === "settings" ? "active" : ""
          }`}
          onClick={() => onSectionChange("settings")}
        >
          <span>⚙️</span>
          <span>Settings</span>
        </button>

      </div>

    </aside>
  );
}

export default Sidebar;