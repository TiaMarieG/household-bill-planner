import { Route, Routes } from "react-router";
import Layout from "./components/Layout.jsx";
import BillsPage from "./pages/BillsPage.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import WeekPage from "./pages/WeekPage.jsx";

/** Page routes, all rendered inside the shared layout. */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CalendarPage />} />
        <Route path="week" element={<WeekPage />} />
        <Route path="bills" element={<BillsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
