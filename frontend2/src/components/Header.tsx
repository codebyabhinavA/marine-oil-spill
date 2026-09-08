function Header() {
  return (
    <header className="header">

      <div className="header-title">
        <h1>Oil Spill Intelligence</h1>
        <p>Satellite Monitoring & Vessel Attribution System</p>
      </div>

      <div className="header-right">

        <div className="status">
          <span className="status-dot"></span>
          System Online
        </div>

        <button className="icon-button">
          🔔
        </button>

        <div className="profile">
          👤
        </div>

      </div>

    </header>
  );
}

export default Header;