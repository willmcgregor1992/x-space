import { render, screen } from "@testing-library/react";
import { JourneyVisualizer } from "./JourneyVisualizer";
import { inflightLaunch, sampleState } from "@/test/fixtures";

describe("JourneyVisualizer", () => {
  it("labels estimated position", () => {
    render(
      <JourneyVisualizer
        launch={inflightLaunch}
        state={sampleState}
        now={new Date("2026-10-23T21:33:00Z")}
        reducedMotion
      />,
    );
    expect(screen.getByText(/Estimated position/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mission journey visualizer/i)).toBeInTheDocument();
  });
});
