/**
 * MavadoClaw Edge Worker - Cloudflare Workers AI Gateway
 * Provides edge-native AI inference, caching, RAG, and routing
 * Free tier: 10,000 neurons/day, 100,000 requests/day
 */

export class AgentState {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === "/state" && request.method === "GET") {
      const data = await this.state.storage.get("state");
      return new Response(JSON.stringify(data || {}), {
        headers: { "Content-Type": "application/json" },
      });
    }

    if (url.pathname === "/state" && request.method === "POST") {
      const body = await request.json();
      await this.state.storage.put("state", body);
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    if (url.pathname === "/state" && request.method === "DELETE") {
      await this.state.storage.deleteAll();
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Not found", { status: 404 });
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    const corsHeaders = {
      "Access-Control-Allow-Origin": env.ALLOWED_ORIGINS || "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      if (path === "/health") {
        return handleHealth(env, corsHeaders);
      }
      if (path === "/api/models") {
        return handleModels(env, corsHeaders);
      }
      if (path === "/api/chat" && request.method === "POST") {
        return handleChat(request, env, corsHeaders);
      }
      if (path === "/api/embed" && request.method === "POST") {
        return handleEmbed(request, env, corsHeaders);
      }
      if (path === "/api/search" && request.method === "POST") {
        return handleSearch(request, env, corsHeaders);
      }
      if (path === "/api/image" && request.method === "POST") {
        return handleImage(request, env, corsHeaders);
      }
      if (path === "/api/rag" && request.method === "POST") {
        return handleRAG(request, env, corsHeaders);
      }

      return new Response(
        JSON.stringify({
          service: "mavadoclaw-edge",
          version: "2.0.0",
          endpoints: {
            health: "/health",
            models: "/api/models",
            chat: "/api/chat (POST)",
            embed: "/api/embed (POST)",
            search: "/api/search (POST)",
            image: "/api/image (POST)",
            rag: "/api/rag (POST)",
          },
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    } catch (err) {
      return new Response(
        JSON.stringify({ error: err.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
  },
};

async function handleHealth(env, headers) {
  return new Response(
    JSON.stringify({
      status: "healthy",
      service: "mavadoclaw-edge",
      platform: "cloudflare-workers-ai",
      features: [
        "Workers AI (80+ models)",
        "Vectorize (vector DB)",
        "D1 (SQL at edge)",
        "R2 (object storage)",
        "Durable Objects (state)",
        "AI Gateway (caching/fallback)",
      ],
    }),
    { headers: { ...headers, "Content-Type": "application/json" } }
  );
}

async function handleModels(env, headers) {
  const models = {
    llm: {
      fast: "@cf/meta/llama-3.2-3b-instruct",
      balanced: "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
      powerful: "@cf/openai/gpt-oss-120b",
      reasoning: "@cf/qwen/qwq-32b",
      coding: "@cf/qwen/qwen2.5-coder-32b-instruct",
      multimodal: "@cf/meta/llama-4-scout-17b-16e-instruct",
      kimi: "@cf/moonshotai/kimi-k2.7-code",
      gemma: "@cf/google/gemma-4-26b-a4b-it",
    },
    embeddings: {
      multilingual: "@cf/baai/bge-m3",
      english: "@cf/baai/bge-large-en-v1.5",
      small: "@cf/baai/bge-small-en-v1.5",
    },
    image: {
      fast: "@cf/black-forest-labs/flux-1-schnell",
      quality: "@cf/black-forest-labs/flux-2-dev",
    },
    audio: {
      asr: "@cf/openai/whisper-large-v3-turbo",
      tts: "@cf/deepgram/aura-2-en",
    },
  };
  return new Response(JSON.stringify({ models }), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function handleChat(request, env, headers) {
  const body = await request.json();
  const { messages, model = "fast", temperature = 0.7, max_tokens = 4096 } = body;

  const MODEL_MAP = {
    fast: "@cf/meta/llama-3.2-3b-instruct",
    balanced: "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    powerful: "@cf/openai/gpt-oss-120b",
    reasoning: "@cf/qwen/qwq-32b",
    coding: "@cf/qwen/qwen2.5-coder-32b-instruct",
    multimodal: "@cf/meta/llama-4-scout-17b-16e-instruct",
    kimi: "@cf/moonshotai/kimi-k2.7-code",
    gemma: "@cf/google/gemma-4-26b-a4b-it",
    small: "@cf/meta/llama-3.2-1b-instruct",
  };

  const cfModel = MODEL_MAP[model] || model;

  const response = await env.AI.run(cfModel, {
    messages,
    temperature,
    max_tokens,
  });

  return new Response(JSON.stringify(response), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function handleEmbed(request, env, headers) {
  const body = await request.json();
  const { texts, model = "small" } = body;

  const EMBED_MAP = {
    multilingual: "@cf/baai/bge-m3",
    english: "@cf/baai/bge-large-en-v1.5",
    small: "@cf/baai/bge-small-en-v1.5",
    qwen: "@cf/qwen/qwen3-embedding-0.6b",
  };

  const cfModel = EMBED_MAP[model] || model;
  const response = await env.AI.run(cfModel, { text: texts });

  return new Response(JSON.stringify(response), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function handleSearch(request, env, headers) {
  const body = await request.json();
  const { query, top_k = 5 } = body;

  const embedResponse = await env.AI.run("@cf/baai/bge-small-en-v1.5", {
    text: [query],
  });

  const vectorQuery = embedResponse.data[0];
  const matches = await env.VECTORIZE.query(vectorQuery, {
    topK: top_k,
    returnMetadata: "all",
  });

  return new Response(JSON.stringify({ query, matches }), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function handleImage(request, env, headers) {
  const body = await request.json();
  const { prompt, model = "fast" } = body;

  const IMAGE_MAP = {
    fast: "@cf/black-forest-labs/flux-1-schnell",
    quality: "@cf/black-forest-labs/flux-2-dev",
  };

  const cfModel = IMAGE_MAP[model] || model;
  const response = await env.AI.run(cfModel, { prompt });

  return new Response(JSON.stringify(response), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

async function handleRAG(request, env, headers) {
  const body = await request.json();
  const { query, context, model = "fast" } = body;

  const embedResponse = await env.AI.run("@cf/baai/bge-small-en-v1.5", {
    text: [query],
  });

  let ragContext = context || "";
  if (env.VECTORIZE) {
    try {
      const matches = await env.VECTORIZE.query(embedResponse.data[0], {
        topK: 3,
        returnMetadata: "all",
      });
      ragContext = matches.matches
        .map((m) => m.metadata?.text || "")
        .filter(Boolean)
        .join("\n\n");
    } catch (e) {
      // Vectorize not configured, use provided context
    }
  }

  const MODEL_MAP = {
    fast: "@cf/meta/llama-3.2-3b-instruct",
    balanced: "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  };

  const messages = [
    {
      role: "system",
      content: `You are a helpful assistant. Use the following context to answer:\n\n${ragContext}`,
    },
    { role: "user", content: query },
  ];

  const response = await env.AI.run(MODEL_MAP[model] || MODEL_MAP.fast, {
    messages,
  });

  return new Response(JSON.stringify(response), {
    headers: { ...headers, "Content-Type": "application/json" },
  });
}
