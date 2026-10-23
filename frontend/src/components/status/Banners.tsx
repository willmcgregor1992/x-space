import { AnimatePresence, motion } from "framer-motion";
import type { Banner } from "@/types";

export function StatusBanners({
  banner,
  simulation,
  launchUpdated,
}: {
  banner: Banner | null | undefined;
  simulation: boolean;
  launchUpdated: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <AnimatePresence>
        {simulation && (
          <motion.div
            key="sim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="panel px-3 py-2 text-ember"
          >
            <p className="label text-ember">Simulation</p>
            <p className="text-xs text-paper/80">
              Development simulator active. This does not persist and is not live telemetry.
            </p>
          </motion.div>
        )}
        {banner && (
          <motion.div
            key={banner.code}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="panel px-3 py-2"
          >
            <p className="label text-live">{banner.title}</p>
            <p className="text-xs text-mist">{banner.message}</p>
          </motion.div>
        )}
        {launchUpdated && (
          <motion.div
            key="updated"
            initial={{ opacity: 0.2 }}
            animate={{ opacity: 1 }}
            className="panel px-3 py-2"
          >
            <p className="label text-ember">Launch time updated</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
