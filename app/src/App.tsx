import { HashRouter, Route, Routes } from "react-router-dom";
import { DataProvider } from "./data/DataProvider";
import { ThemeProvider } from "./theme/ThemeContext";
import { OnboardingProvider } from "./onboarding/OnboardingContext";
import { OnboardingTour } from "./onboarding/OnboardingTour";
import { Layout } from "./components/Layout";
import { LandingPage } from "./pages/LandingPage";
import { BoardPage } from "./pages/BoardPage";
import { StatsPage } from "./pages/StatsPage";
import { ProspectDetailPage } from "./pages/ProspectDetailPage";
import { TeamNeedPage } from "./pages/TeamNeedPage";
import { AboutPage } from "./pages/AboutPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { AnalyzePage } from "./pages/AnalyzePage";

// HashRouter: the production build is static files with no server-side
// rewrite rule guaranteed, so a hash route (#/board) works on any static
// host without extra deployment configuration.
function App() {
  return (
    <ThemeProvider>
      <DataProvider>
        <HashRouter>
        <OnboardingProvider>
          <Routes>
            {/* Landing has no Layout chrome — it's the entry screen, not a
               product page. */}
            <Route index element={<LandingPage />} />
            <Route element={<Layout />}>
              <Route path="board" element={<BoardPage />} />
              <Route path="stats" element={<StatsPage />} />
              <Route path="prospect/:id" element={<ProspectDetailPage />} />
              <Route path="team-need" element={<TeamNeedPage />} />
              <Route path="methodology" element={<AboutPage />} />
              <Route path="2027" element={<WatchlistPage />} />
              <Route path="analyze" element={<AnalyzePage />} />
            </Route>
          </Routes>
          <OnboardingTour />
        </OnboardingProvider>
        </HashRouter>
      </DataProvider>
    </ThemeProvider>
  );
}

export default App;
