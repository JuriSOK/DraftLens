import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import styles from "./Layout.module.css";

const NAV_LINKS = [
  { to: "/board", label: "Board" },
  { to: "/stats", label: "Stats" },
  { to: "/team-need", label: "Team Need" },
  { to: "/methodology", label: "Methodology" },
];

export function Layout() {
  const location = useLocation();
  const on2027 = location.pathname.startsWith("/2027");

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          <Link to="/" className={styles.brand}>
            <span className={styles.brandMark} aria-hidden="true" />
            DraftLens
          </Link>
          <nav className={styles.nav} aria-label="Primary">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  isActive && !on2027
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
              to="/board"
              className={on2027 ? styles.yearButton : `${styles.yearButton} ${styles.yearButtonActive}`}
            >
              2026
            </NavLink>
            <NavLink
              to="/2027"
              className={on2027 ? `${styles.yearButton} ${styles.yearButtonActive}` : styles.yearButton}
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
