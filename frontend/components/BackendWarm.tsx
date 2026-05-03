"use client";

import { useEffect } from "react";
import { warmBackend } from "@/lib/api";

export default function BackendWarm() {
  useEffect(() => {
    warmBackend();
  }, []);
  return null;
}
