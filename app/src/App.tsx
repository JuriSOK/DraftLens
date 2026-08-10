import { HashRouter, Route, Routes } from "react-router-dom";
import { DataProvider } from "./data/DataProvider";
import { Layout } from "./components/Layout";
import { BoardPage } from "./pages/BoardPage";
import { StatsPage } from "./pages/StatsPage";
import { ProspectDetailPage } from "./pages/ProspectDetailPage";
import { TeamNeedPage } from "./pages/TeamNeedPage";
import { AboutPage } from "./pages/AboutPage";
import { WatchlistPage } from "./pages/WatchlistPage";

// HashRouter: the production build is static files with no server-side
// rewrite rule guaranteed, so a hash route (#/prospect/:id) works on any
// static host without extra deployment configuration.
function App() {
  return (
    <DataProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<BoardPage />} />
            <Route path="stats" element={<StatsPage />} />
            <Route path="prospect/:id" element={<ProspectDetailPage />} />
            <Route path="team-need" element={<TeamNeedPage />} />
            <Route path="about" element={<AboutPage />} />
            <Route path="watchlist" element={<WatchlistPage />} />
          </Route>
        </Routes>
      </HashRouter>
    </DataProvider>
  );
}

export default App;
