import { createBrowserRouter } from "react-router-dom";
import LayoutShell from "../components/layout/LayoutShell";
import Dashboard from "../pages/Dashboard";
import JobDetail from "../pages/JobDetail";
import NewJob from "../pages/NewJob";
import Technicians from "../pages/Technicians";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <LayoutShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "jobs/new", element: <NewJob /> },
      { path: "jobs/:id", element: <JobDetail /> },
      { path: "technicians", element: <Technicians /> },
    ],
  },
]);
