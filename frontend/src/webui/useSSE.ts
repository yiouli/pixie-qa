/** SSE hook for live artifact updates */

import { useEffect, useRef } from "react";
import type { Manifest, FileChangeEvent, NavigateEvent } from "./types";

interface UseSSEOptions {
  onManifest: (manifest: Manifest) => void;
  onFileChange: (changes: FileChangeEvent[]) => void;
  onNavigate: (nav: NavigateEvent) => void;
}

export function useSSE({
  onManifest,
  onFileChange,
  onNavigate,
}: UseSSEOptions): void {
  const onManifestRef = useRef(onManifest);
  const onFileChangeRef = useRef(onFileChange);
  const onNavigateRef = useRef(onNavigate);

  useEffect(() => {
    onManifestRef.current = onManifest;
    onFileChangeRef.current = onFileChange;
    onNavigateRef.current = onNavigate;
  });

  useEffect(() => {
    const es = new EventSource("/api/events");

    es.addEventListener("manifest", (e) => {
      const data = JSON.parse(e.data) as Manifest;
      onManifestRef.current(data);
    });

    es.addEventListener("file_change", (e) => {
      const data = JSON.parse(e.data) as FileChangeEvent[];
      onFileChangeRef.current(data);
    });

    es.addEventListener("navigate", (e) => {
      const data = JSON.parse(e.data) as NavigateEvent;
      onNavigateRef.current(data);
    });

    return () => es.close();
  }, []);
}
