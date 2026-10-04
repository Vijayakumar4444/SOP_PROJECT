import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createPortal } from "react-dom";
import { useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { getSimulationProgress } from "../../api/simulations.api";
import dataCompatibilityIcon from "../../assets/loading/data-compatibility.png";
import syntheticPopulationIcon from "../../assets/loading/synthetic-population.png";
import populationValidationIcon from "../../assets/loading/population-validation.png";
import calibrationIcon from "../../assets/loading/calibration-reweighing.png";
import monteCarloIcon from "../../assets/loading/monte-carlo.png";

const STAGE_DURATION_MS = 2000;

const stages = [
  { title: "DATA COMPATIBILITY", image: dataCompatibilityIcon },
  { title: "SYNTHETIC POPULATION GENERATION", image: syntheticPopulationIcon },
  { title: "POPULATION VALIDATION", image: populationValidationIcon },
  { title: "CALIBRATION AND REWEIGHING", image: calibrationIcon },
  { title: "MONTE CARLO ENGINE", image: monteCarloIcon }
];

export default function SimulationProgress() {
  const { simulationId = "SIM-TN-2026-1042" } = useParams();
  const navigate = useNavigate();
  const [elapsedMs, setElapsedMs] = useState(0);
  const { data: progress, isError, error } = useQuery({
    queryKey: ["simulation-progress", simulationId],
    queryFn: () => getSimulationProgress(simulationId),
    refetchInterval: 1500,
    retry: true
  });

  const totalDuration = stages.length * STAGE_DURATION_MS;
  const realProgress = progress?.progress ?? Math.min(99, Math.max(4, Math.floor((elapsedMs / totalDuration) * 100)));
  const stageIndex = Math.min(stages.length - 1, Math.floor((realProgress / 100) * stages.length));
  const activeStage = stages[stageIndex];
  const pipelineComplete = progress?.pipelineStatus === "completed";
  const pipelineFailed = progress?.pipelineStatus === "failed" || progress?.stages.some((stage) => stage.status === "failed");

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAt);
    }, 100);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, []);

  useEffect(() => {
    if (pipelineComplete && !pipelineFailed) {
      const timer = window.setTimeout(() => navigate(`/results/${simulationId}`), 250);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [navigate, pipelineComplete, pipelineFailed, simulationId]);

  const stageKey = useMemo(() => `${stageIndex}-${activeStage.title}`, [activeStage.title, stageIndex]);

  return createPortal(
    <main
      className="z-50 overflow-hidden overscroll-none bg-white text-black"
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        display: "grid",
        placeItems: "center"
      }}
    >
      <AnimatePresence mode="wait">
        <motion.section
          key={stageKey}
          className="px-6 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.32, ease: "easeOut" }}
        >
          <div className="flex max-w-5xl flex-col items-center justify-center gap-8">
            <motion.img
              src={activeStage.image}
              alt=""
              className="block object-contain"
              style={{ width: 150, height: 150, maxWidth: "34vw", maxHeight: "28vh" }}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.45, ease: "easeOut" }}
            />
            <motion.h1
              className="max-w-5xl text-balance text-center font-mono text-4xl font-black uppercase leading-tight tracking-normal text-black sm:text-5xl lg:text-6xl"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, delay: 0.08, ease: "easeOut" }}
            >
              {pipelineFailed ? "PIPELINE FAILED" : progress?.currentStage ?? activeStage.title}
            </motion.h1>
            <div className="w-full max-w-xl border-2 border-black bg-white p-3">
              <div className="h-3 bg-gov-50">
                <div className="h-3 bg-gov-700" style={{ width: `${Math.min(100, realProgress)}%` }} />
              </div>
              <div className="mt-3 flex items-center justify-between gap-4 font-mono text-sm font-bold uppercase">
                <span>{Math.round(realProgress)}%</span>
                <span>{progress ? `${progress.completedIterations}/${progress.totalIterations} phases` : "Starting backend"}</span>
              </div>
              {isError ? <div className="mt-2 text-sm font-bold text-red-700">{error instanceof Error ? error.message : "Unable to read backend progress"}</div> : null}
              {pipelineFailed ? <div className="mt-2 text-sm font-bold text-red-700">The backend pipeline stopped before Phase 8. Check backend logs for the failed phase.</div> : null}
            </div>
          </div>
        </motion.section>
      </AnimatePresence>
    </main>,
    document.body
  );
}
