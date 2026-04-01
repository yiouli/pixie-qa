/** SSE hook for live artifact updates */

import { useEffect, useRef } from "react";
import type { Manifest, FileChangeEvent } from "./types";

interface UseSSEOptions {
  onManifest: (manifest: Manifest) => void;
  onFileChange: (changes: FileChangeEvent[]) => void;
}

export function useSSE({ onManifest, onFileChange }: UseSSEOptions): void {
  const onManifestRef = useRef(onManifest);
  const onFileChangeRef = useRef(onFileChange);

  useEffect(() => {
    onManifestRef.current = onManifest;
    onFileChangeRef.current = onFileChange;
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

    return () => es.close();
  }, []);
}
