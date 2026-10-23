import "@testing-library/jest-dom/vitest";

class EventSourceMock {
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  close() {}
}

Object.defineProperty(window, "EventSource", {
  writable: true,
  value: EventSourceMock,
});
