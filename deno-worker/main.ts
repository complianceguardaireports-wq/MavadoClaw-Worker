/// <reference no-default-lib="true" />
/// <reference lib="deno.worker" />

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

const BACKEND_URL = Deno.env.get("BACKEND_URL") || "https://mavadoclaw-backend.onrender.com";
const ALLOWED_ORIGINS = Deno.env.get("ALLOWED_ORIGINS") || "*";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGINS,
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

async function proxyToBackend(path: string, request: Request): Promise<Response> {
  const url = new URL(path, BACKEND_URL);
  const body = request.method === "GET" || request.method === "OPTIONS" ? undefined : await request.text();
  const resp = await fetch(url.href, {
    method: request.method,
    headers: { "Content-Type": "application/json" },
    body,
  });
  const data = await resp.text();
  return new Response(data, {
    status: resp.status,
    headers: { ...CORS_HEADERS, "Content-Type": resp.headers.get("Content-Type") || "application/json" },
  });
}

async function handler(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;

  if (request.method === "OPTIONS") {
    return new Response(null, { headers: CORS_HEADERS });
  }

  if (path === "/health") {
    return jsonResponse({
      status: "healthy",
      service: "mavadoclaw-edge",
      platform: "deno-deploy",
      backend: BACKEND_URL,
    });
  }

  if (path === "/") {
    return jsonResponse({
      service: "mavadoclaw-edge",
      version: "2.0.0",
      platform: "deno-deploy",
      backend: BACKEND_URL,
      endpoints: {
        health: "/health",
        chat: "/api/chat (POST)",
        task: "/api/task (POST)",
        agents: "/api/agents (GET)",
        status: "/api/status (GET)",
        deploy: "/api/deploy (POST)",
      },
    });
  }

  if (path.startsWith("/api/")) {
    return proxyToBackend(path, request);
  }

  return new Response("Not found", { status: 404, headers: CORS_HEADERS });
}

serve(handler);
