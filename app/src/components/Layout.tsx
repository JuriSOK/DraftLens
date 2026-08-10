import { NavLink, Outlet } from "react-router-dom";
import styles from "./Layout.module.css";

const NAV_LINKS = [
  { to: "/", label: "Board", end: true },
  { to: "/team-need", label: "Team Need" },
  { to: "/about", label: "Methodology" },
];

export function Layout() {
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
                  isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
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
