import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import Home from "../pages/Home";

const PromptManager = lazy(() => import("../pages/PromptManager"));
const Watchlist = lazy(() => import("../pages/Watchlist"));
const AIPrediction = lazy(() => import("../pages/AIPrediction"));
const PredictionTrack = lazy(() => import("../pages/PredictionTrack"));

function LazyPage({ Component }: { Component: React.LazyExoticComponent<React.ComponentType> }) {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-24"><span className="text-sm text-muted-foreground">加载中...</span></div>}>
      <Component />
    </Suspense>
  );
}

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/prompts", element: <LazyPage Component={PromptManager} /> },
      { path: "/watchlist", element: <LazyPage Component={Watchlist} /> },
      { path: "/prediction/:stock", element: <LazyPage Component={AIPrediction} /> },
      { path: "/prediction-track", element: <LazyPage Component={PredictionTrack} /> },
    ],
  },
]);

export default router;
