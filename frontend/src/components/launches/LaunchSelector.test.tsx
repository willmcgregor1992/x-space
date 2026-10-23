import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LaunchSelector } from "./LaunchSelector";
import { sampleLaunch } from "@/test/fixtures";

describe("LaunchSelector", () => {
  it("selects another upcoming launch", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const second = { ...sampleLaunch, id: "sl-15-16", slug: "sl-15-16", mission_name: "Starlink 15-16" };
    render(
      <LaunchSelector
        tab="UPCOMING"
        onTab={() => undefined}
        launches={[sampleLaunch, second]}
        selectedId="sl-15-15"
        onSelect={onSelect}
        clockMode="UTC"
        now={new Date("2026-10-23T12:00:00Z")}
      />,
    );
    await user.click(screen.getByText("Starlink 15-16"));
    expect(onSelect).toHaveBeenCalledWith("sl-15-16");
  });
});
