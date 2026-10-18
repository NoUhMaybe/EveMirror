import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  initialState,
  receive,
  type DashboardState,
  type View,
} from "../state/dashboard";
import {
  ApiError,
  DashboardClient,
  request,
  backoff,
} from "../transport/client";
import type { BrowserSession } from "../types/contracts";

type Context = {
  state: DashboardState;
  session: BrowserSession | null;
  code: string;
  pairingError: string;
  pair: () => Promise<void>;
  action: (name: string, args?: Record<string, unknown>) => Promise<void>;
  mute: (muted: boolean) => Promise<void>;
  cancel: () => Promise<void>;
  logout: () => Promise<void>;
  pending: boolean;
  notice: string;
  dismissNotice: () => void;
  view: (view: View) => Promise<void>;
};
const AppContext = createContext<Context | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialState);
  const [session, setSession] = useState<BrowserSession | null>(null);
  const [code, setCode] = useState("");
  const [pairingError, setPairingError] = useState("");
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false,
      attempt = 0;
    const bootstrap = async () => {
      try {
        const value = await request<{ session: BrowserSession }>("/session", {
          signal: controller.signal,
        });
        if (!stopped) setSession(value.session);
      } catch (error) {
        if (stopped) return;
        if (error instanceof ApiError && [401, 403].includes(error.status)) {
          setState((s) => ({ ...s, network: "unpaired" }));
        } else {
          setState((s) => ({ ...s, network: "offline" }));
          timer = setTimeout(() => void bootstrap(), backoff(attempt++));
        }
      }
    };
    void bootstrap();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, []);
  useEffect(() => {
    if (!session) return;
    const client = new DashboardClient(
      session,
      (frame) => {
        setState((s) => receive(s, frame));
      },
      (error, unauthorized) => {
        if (unauthorized) {
          setSession(null);
          setCode("");
          setState({
            ...initialState(),
            network: "unpaired",
            error: "This display needs to be paired again.",
          });
        } else
          setState((s) => ({
            ...s,
            network: "offline",
            voice: { ...s.voice, playing: false, transcript: "", response: "" },
            error: error.message,
          }));
      },
    );
    client.start();
    return () => client.stop();
  }, [session?.id]);
  useEffect(() => {
    if (!code || session) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const check = async () => {
      try {
        const result = await request<{
          status: string;
          session?: BrowserSession;
        }>("/pairings", { signal: controller.signal });
        if (stopped) return;
        if (result.session) {
          setSession(result.session);
          setCode("");
          return;
        }
      } catch (error) {
        if (stopped) return;
        if (error instanceof ApiError && error.status === 401) {
          setPairingError("This code expired. Request a new one.");
          setCode("");
          return;
        }
      }
      if (!stopped) timer = setTimeout(() => void check(), 1500);
    };
    void check();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [code, session]);
  const pair = useCallback(async () => {
    setPairingError("");
    try {
      const result = await request<{ code: string }>("/pairings", {
        method: "POST",
        body: JSON.stringify({ name: "Eve mirror display" }),
      });
      setCode(result.code);
    } catch {
      setPairingError(
        "Pairing is unavailable. Check the connection and browser configuration.",
      );
    }
  }, []);
  const write = useCallback(
    async (path: string, body: unknown = {}) => {
      if (state.network !== "online" || !state.frame || pending) return false;
      setPending(true);
      setNotice("");
      try {
        const result = await request<{
          status?: string;
          error?: { message?: string };
          data?: { acknowledged?: boolean; verified?: boolean };
        }>(path, {
          method: "POST",
          headers: { "X-Eve-CSRF": state.frame.session.csrf },
          body: JSON.stringify(body),
        });
        if (result.status === "error") {
          setNotice(
            result.error?.message ?? "The action could not be confirmed.",
          );
          return false;
        } else if (result.data?.acknowledged && !result.data.verified)
          setNotice(
            "Command acknowledged. The device's new state has not been confirmed.",
          );
        return true;
      } catch (error) {
        setNotice(
          error instanceof ApiError && error.status === 403
            ? "This display does not have permission for that action."
            : "The result is unknown. Check the state before trying again.",
        );
        return false;
      } finally {
        setPending(false);
      }
    },
    [state.network, state.frame, pending],
  );
  const action = useCallback(
    async (name: string, args: Record<string, unknown> = {}) => {
      await write("/actions", {
        request_id: crypto.randomUUID(),
        name,
        arguments: args,
      });
    },
    [write],
  );
  const logout = useCallback(async () => {
    if (!(await write("/session/logout"))) return;
    setSession(null);
    setState({ ...initialState(), network: "unpaired" });
  }, [write]);
  return (
    <AppContext.Provider
      value={{
        state,
        session: state.frame?.session ?? session,
        code,
        pairingError,
        pair,
        action,
        pending,
        notice,
        dismissNotice: () => setNotice(""),
        view: (view) => action("dashboard.show_view", { view }),
        mute: async (muted) => {
          await write("/voice/mute", { muted });
        },
        cancel: async () => {
          await write("/voice/cancel");
        },
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}
export function useDashboard() {
  const value = useContext(AppContext);
  if (!value) throw Error("Dashboard provider is missing");
  return value;
}
