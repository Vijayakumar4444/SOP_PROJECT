import { Outlet } from "react-router-dom";
import { motion } from "framer-motion";

export function AppShell() {
  return (
    <div className="min-h-screen bg-white text-ink">
      <div className="border-b-2 border-ink bg-white">
        <div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div>
            <div className="text-lg font-bold uppercase tracking-wide text-ink">PolicySim TN</div>
            <div className="text-xs font-semibold uppercase text-gov-900">Government Policy Simulation Intelligence</div>
          </div>
          <div className="hidden border-2 border-ink px-3 py-1 font-mono text-xs font-semibold sm:block">FASTAPI READY</div>
        </div>
      </div>
      <motion.main
        className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <Outlet />
      </motion.main>
    </div>
  );
}
