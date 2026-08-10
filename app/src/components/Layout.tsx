import { NavLink, Outlet, useLocation } from "react-router-dom";
import styles from "./Layout.module.css";

const NAV_LINKS = [
  { to: "/", label: "Board", end: true },
  { to: "/stats", label: "Stats" },
  { to: "/team-need", label: "Team Need" },
  { to: "/about", label: "Methodology" },
];

export function Layout() {
  const location = useLocation();
  const onWatchlist = location.pathname.startsWith("/watchlist");

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          <NavLink to="/" className={styles.brand}>
            <span className={styles.brandMark} aria-hidden="true" />
            DraftLens
          </NavLink>
          <nav className={styles.nav} aria-label="Primary">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  isActive && !onWatchlist
                    ? `${styles.navLink} ${styles.navLinkActive}`
                    : styles.navLink
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className={styles.yearToggle} role="group" aria-label="Draft class year">
            <NavLink
              to="/"
              className={onWatchlist ? styles.yearButton : `${styles.yearButton} ${styles.yearButtonActive}`}
            >
              2026
            </NavLink>
            <NavLink
              to="/watchlist"
              className={onWatchlist ? `${styles.yearButton} ${styles.yearButtonActive}` : styles.yearButton}
            >
              2027 Watchlist
            </NavLink>
          </div>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <div className={`container ${styles.footerInner}`}>
          <span>DraftLens — AQX Sports Analytics Data Bowl 3.0</span>
          <span>Pre-draft analytics. No 2026 outcome is used as product input.</span>
        </div>
      </footer>
    </div>
  );
}
