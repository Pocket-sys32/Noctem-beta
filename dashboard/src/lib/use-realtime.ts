"use client";

import { useEffect } from "react";
import { createClient } from "./supabase";

/**
 * Subscribe to Supabase Realtime changes on a table.
 * When the voice agent updates carrier_profiles, the dashboard refreshes live.
 */
export function useRealtimeTable(
  table: string,
  filter: string | undefined,
  onUpdate: () => void
) {
  useEffect(() => {
    const sb = createClient();
    const channel = sb
      .channel(`realtime-${table}`)
      .on(
        "postgres_changes" as any,
        {
          event: "*",
          schema: "public",
          table,
          ...(filter ? { filter } : {}),
        },
        () => {
          onUpdate();
        }
      )
      .subscribe();

    return () => {
      sb.removeChannel(channel);
    };
  }, [table, filter, onUpdate]);
}
