import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, RouterProvider, createBrowserRouter, useParams } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./index.css";
import { AppShell } from "./components/layout/AppShell";
import { PageLoader } from "./components/ui/PageLoader";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";

const NewSimulation = lazy(() => import("./pages/NewSimulation/NewSimulation"));
const SimulationProgress = lazy(() => import("./pages/SimulationProgress/SimulationProgress"));
const SimulationResults = lazy(() => import("./pages/SimulationResults/SimulationResults"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

const withPage = (element: React.ReactNode) => (
  <ErrorBoundary>
    <Suspense fallback={<PageLoader />}>{element}</Suspense>
  </ErrorBoundary>
);

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: withPage(<NewSimulation />) },
      { path: "loading/:simulationId", element: withPage(<SimulationProgress />) },
      { path: "results/:simulationId", element: withPage(<SimulationResults />) },
      { path: "new-simulation", element: <Navigate to="/" replace /> },
      { path: "simulations/:simulationId/progress", element: <LegacyRedirect target="loading" /> },
      { path: "simulations/:simulationId/results", element: <LegacyRedirect target="results" /> },
      { path: "*", element: <Navigate to="/" replace /> }
    ]
  }
]);

function LegacyRedirect({ target }: { target: "loading" | "results" }) {
  const { simulationId = "SIM-TN-2026-1042" } = useParams();
  return <Navigate to={`/${target}/${simulationId}`} replace />;
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
