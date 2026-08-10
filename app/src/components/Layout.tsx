import { Link, NavLink, Outlet } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";
import styles from "./Layout.module.css";

// Served from app/public/, so the same tracked file backs the in-app mark
// and the README's logo — one asset, no duplicated binary.
const LOGO = `${import.meta.env.BASE_URL}brand/draftlens-logo.png`;

const NAV_LINKS = [
  { to: "/board", label: "Board" },
  { to: "/stats", label: "Stats" },
  { to: "/team-need", label: "Team Need" },
  { to: "/analyze", label: "Analyze Data" },
  { to: "/methodology", label: "Methodology" },
];

export function Layout() {

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          {/* Inside the product, the Board is home — the landing page at "/"
             is only the entry screen, so the brand never navigates back to
             it. Layout wraps every in-app route, so this is the single
             definition of that behaviour. */}
          <Link to="/board" className={styles.brand} aria-label="DraftLens">
            <img className={styles.brandLogo} src={LOGO} alt="DraftLens"
                 width={500} height={500} />
          </Link>
          <nav className={styles.nav} aria-label="Primary">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  isActive ? `${styles.navLink} ${styles.navLinkActive}`
                    : styles.navLink
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className={styles.headerActions}>
          <ThemeToggle />
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
