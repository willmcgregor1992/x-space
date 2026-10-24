import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { inflightLaunch, sampleLaunch, sampleState } from "@/test/fixtures";
import { DashboardPage } from "./DashboardPage";

vi.mock("@/hooks/useMissionData", () => ({
  useMissionData: () => ({
    launch: inflightLaunch,
    state: sampleState,
    meta: {
      server_time: "2026-10-23T21:33:00Z",
      data_updated_at: "2026-10-23T21:30:00Z",
      stale_seconds: 180,
      used_cache: false,
      banner: null,
      simulation: false,
    },
    upcoming: [sampleLaunch],
    recent: [],
    live: [inflightLaunch],
    currentId: inflightLaunch.id,
    isLoading: false,
    isError: false,
    error: null,
    simulation: false,
    refetchAll: () => undefined,
  }),
}));

vi.mock("@/hooks/useEventStream", () => ({
  useEventStream: () => undefined,
}));

vi.mock("@/components/rocket/RocketModel", () => ({
  RocketModel: ({ config }: { config: { caption: string } }) => <div>{config.caption}</div>,
  preloadRocket: () => undefined,
}));

function renderDash() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe("dashboard", () => {
  it("renders mission control chrome and estimated labels", () => {
    renderDash();
    expect(screen.getByText(/MISSION CONTROL/)).toBeInTheDocument();
    expect(screen.getAllByText(/Estimated/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: "UPCOMING" })).toBeInTheDocument();
  });
});

