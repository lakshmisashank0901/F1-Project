"use client";

import { useEffect, useState } from "react";
import { emptySnapshot, type Snapshot } from "@/lib/types";

const socketUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8001/ws";

export function useRace() {
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      socket = new WebSocket(socketUrl);
      socket.onmessage = (event) => {
        setSnapshot(JSON.parse(event.data) as Snapshot);
      };
      socket.onclose = () => {
        if (!stopped) timer = setTimeout(connect, 1500);
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, []);

  return snapshot;
}
