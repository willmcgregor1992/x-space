import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ClockMode } from "@/utils/time";

interface PreferencesState {
  clockMode: ClockMode;
  setClockMode: (mode: ClockMode) => void;
}

export const usePreferences = create<PreferencesState>()(
  persist(
    (set) => ({
      clockMode: "UTC",
      setClockMode: (clockMode) => set({ clockMode }),
    }),
    { name: "sxmc-preferences" },
  ),
);
