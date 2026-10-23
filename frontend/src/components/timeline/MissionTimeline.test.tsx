import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MissionTimeline } from "./MissionTimeline";
import { inflightLaunch, sampleState } from "@/test/fixtures";

describe("MissionTimeline", () => {
  it("shows estimated milestone details on click", async () => {
    const user = userEvent.setup();
    render(
      <MissionTimeline
        launch={inflightLaunch}
        state={sampleState}
        now={new Date("2026-10-23T21:33:00Z")}
      />,
    );
    await user.click(screen.getByLabelText(/Max Q/i));
    expect(screen.getByText(/Estimated from mission profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Peak pressure/)).toBeInTheDocument();
  });
});
