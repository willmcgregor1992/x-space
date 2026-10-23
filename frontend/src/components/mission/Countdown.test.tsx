import { render, screen } from "@testing-library/react";
import { Countdown } from "./Countdown";
import { inflightLaunch, sampleState } from "@/test/fixtures";

describe("Countdown", () => {
  it("shows T+ after liftoff", () => {
    render(
      <Countdown
        launch={inflightLaunch}
        state={sampleState}
        now={new Date("2026-10-23T21:31:43Z")}
      />,
    );
    expect(screen.getByText("T+")).toBeInTheDocument();
    expect(screen.getByText("01:43")).toBeInTheDocument();
  });
});
