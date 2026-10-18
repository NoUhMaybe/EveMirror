import { useState } from "react";
import { useDashboard } from "../app/AppProvider";

type Entity = {
  entity_id: string;
  name: string;
  state: string;
  observed_at: string;
  capabilities: string[];
  attributes: Record<string, unknown>;
  power_on?: boolean;
  power_off?: boolean;
  remote_commands?: string[];
};
function entity(input: unknown): input is Entity {
  if (!input || typeof input !== "object") return false;
  const value = input as Record<string, unknown>;
  return (
    typeof value.entity_id === "string" &&
    typeof value.state === "string" &&
    typeof value.name === "string" &&
    Array.isArray(value.capabilities) &&
    !!value.attributes &&
    typeof value.attributes === "object"
  );
}

export default function Home({ media = false }: { media?: boolean }) {
  const { state, session, pending, action } = useDashboard();
  const [requestedPage, setPage] = useState(0);
  const latest = state.frame?.home ?? [];
  const cached =
    state.frame?.application.devices?.filter((x) => x.entity_id) ?? [];
  const entries = (latest.length ? latest : cached)
    .filter(entity)
    .filter((x) => media === x.entity_id.startsWith("media_player."));
  const page = Math.min(
    requestedPage,
    Math.max(0, Math.ceil(entries.length / 3) - 1),
  );
  const current = entries.slice(page * 3, page * 3 + 3);
  const available =
    state.network === "online" &&
    !state.frame?.application.availability?.home_error &&
    latest.length > 0;
  const allowed =
    available &&
    state.frame?.application.availability?.mutations_enabled === true &&
    !!session?.permissions.home_control &&
    !pending;
  return (
    <section
      className="widget home"
      data-testid={media ? "media" : "smart-home"}
    >
      <div className="widget-heading">
        <div>
          <p className="eyebrow">
            {media ? "Set the mood" : "Your space, considered"}
          </p>
          <h2>{media ? "Now playing" : "At home"}</h2>
        </div>
        <span className="source-badge">
          {available ? "Observed" : "Unavailable"}
        </span>
      </div>
      {!entries.length && (
        <p className="empty-copy">
          {state.frame?.application.availability?.home_configured
            ? "No approved devices are available in this display's scope."
            : "Home Assistant has not been configured."}
        </p>
      )}
      {current.map((item) => {
        const caps = item.capabilities;
        const enabled =
          allowed && !["unknown", "unavailable"].includes(item.state);
        const call = (name: string, args: Record<string, unknown> = {}) =>
          void action(name, { target: item.entity_id, ...args });
        return (
          <article className="entity" key={item.entity_id}>
            <div className="entity-heading">
              <div>
                <h3>{item.name}</h3>
                <p>
                  {media && typeof item.attributes.media_title === "string"
                    ? item.attributes.media_title
                    : item.state.replaceAll("_", " ")}
                </p>
              </div>
              <span className={`entity-state ${available ? "" : "stale"}`}>
                {available ? item.state : "Last known"}
              </span>
            </div>
            <div className="entity-controls">
              {caps.includes("turn_on") && (
                <button
                  disabled={!enabled}
                  onClick={() => call("home.turn_on")}
                >
                  On
                </button>
              )}
              {caps.includes("turn_off") && (
                <button
                  disabled={!enabled}
                  onClick={() => call("home.turn_off")}
                >
                  Off
                </button>
              )}
              {caps.includes("activate_scene") && (
                <button
                  disabled={!enabled}
                  onClick={() => call("home.activate_scene")}
                >
                  Activate scene
                </button>
              )}
              {caps.includes("power") && item.power_on === true && (
                <button
                  disabled={!enabled}
                  onClick={() => call("media.power", { on: true })}
                >
                  Power on
                </button>
              )}
              {caps.includes("power") && item.power_off === true && (
                <button
                  disabled={!enabled}
                  onClick={() => call("media.power", { on: false })}
                >
                  Power off
                </button>
              )}
              {caps.includes("play") && (
                <button disabled={!enabled} onClick={() => call("media.play")}>
                  Play
                </button>
              )}
              {caps.includes("pause") && (
                <button disabled={!enabled} onClick={() => call("media.pause")}>
                  Pause
                </button>
              )}
              {caps.includes("stop") && (
                <button disabled={!enabled} onClick={() => call("media.stop")}>
                  Stop
                </button>
              )}
              {caps.includes("send_remote_command") &&
                item.remote_commands?.map((command) => (
                  <button
                    key={command}
                    disabled={!enabled}
                    onClick={() =>
                      call("media.send_remote_command", { command })
                    }
                  >
                    {command.replaceAll("_", " ")}
                  </button>
                ))}
              {caps.includes("set_level") && (
                <label>
                  Brightness
                  <input
                    aria-label={`${item.name} brightness`}
                    type="range"
                    min="0"
                    max="100"
                    defaultValue={
                      typeof item.attributes.brightness === "number"
                        ? (item.attributes.brightness / 255) * 100
                        : 50
                    }
                    disabled={!enabled}
                    onPointerUp={(event) =>
                      call("home.set_level", {
                        percent: Number(event.currentTarget.value),
                      })
                    }
                    onKeyUp={(event) => {
                      if (event.key.startsWith("Arrow"))
                        call("home.set_level", {
                          percent: Number(event.currentTarget.value),
                        });
                    }}
                  />
                </label>
              )}
              {caps.includes("set_volume") && (
                <label>
                  Volume
                  <input
                    aria-label={`${item.name} volume`}
                    type="range"
                    min="0"
                    max="100"
                    defaultValue={
                      typeof item.attributes.volume_level === "number"
                        ? item.attributes.volume_level * 100
                        : 0
                    }
                    disabled={!enabled}
                    onPointerUp={(event) =>
                      call("media.set_volume", {
                        percent: Number(event.currentTarget.value),
                      })
                    }
                    onKeyUp={(event) => {
                      if (event.key.startsWith("Arrow"))
                        call("media.set_volume", {
                          percent: Number(event.currentTarget.value),
                        });
                    }}
                  />
                </label>
              )}
              {caps.includes("select_source") &&
                Array.isArray(item.attributes.source_list) && (
                  <label>
                    Source
                    <select
                      disabled={!enabled}
                      value={String(item.attributes.source ?? "")}
                      onChange={(event) =>
                        call("media.select_source", {
                          source: event.target.value,
                        })
                      }
                    >
                      <option value="" disabled>
                        Select source
                      </option>
                      {item.attributes.source_list
                        .filter((x): x is string => typeof x === "string")
                        .map((source) => (
                          <option key={source}>{source}</option>
                        ))}
                    </select>
                  </label>
                )}
            </div>
            <p className="provenance">
              {available ? "Home Assistant observation" : "Cached observation"}{" "}
              ·{" "}
              {item.observed_at
                ? new Date(item.observed_at).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })
                : "Time unavailable"}
            </p>
          </article>
        );
      })}
      {entries.length > 3 && (
        <div className="pagination">
          <button disabled={!page} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <button
            disabled={(page + 1) * 3 >= entries.length}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}
