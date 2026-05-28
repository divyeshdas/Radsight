"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type WSStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions {
  onMessage?: (data: unknown) => void;
  reconnectDelay?: number;
  maxRetries?: number;
}

export function useWebSocket(path: string, options: UseWebSocketOptions = {}) {
  const { onMessage, reconnectDelay = 3000, maxRetries = 10 } = options;
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const url = `${wsBase}${path}`;

    try {
      setStatus("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        retriesRef.current = 0;
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          onMessage?.(data);
        } catch {}
      };

      ws.onclose = () => {
        setStatus("disconnected");
        if (retriesRef.current < maxRetries) {
          retriesRef.current += 1;
          timeoutRef.current = setTimeout(connect, reconnectDelay);
        }
      };

      ws.onerror = () => {
        setStatus("error");
        ws.close();
      };
    } catch {
      setStatus("error");
    }
  }, [path, onMessage, reconnectDelay, maxRetries]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(timeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status };
}
