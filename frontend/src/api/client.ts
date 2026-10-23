import type {
  CurrentResponse,
  LaunchDetailResponse,
  LaunchListResponse,
} from "@/types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  current: (simulate?: string | null) =>
    getJson<CurrentResponse>(simulate ? `/api/current?simulate=${simulate}` : "/api/current"),
  upcoming: () => getJson<LaunchListResponse>("/api/launches/upcoming"),
  recent: () => getJson<LaunchListResponse>("/api/launches/recent"),
  live: () => getJson<LaunchListResponse>("/api/launches/live"),
  launch: (id: string, simulate?: string | null) =>
    getJson<LaunchDetailResponse>(
      simulate ? `/api/launches/${id}?simulate=${simulate}` : `/api/launches/${id}`,
    ),
};
