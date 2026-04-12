import { z } from "zod";
import { tool } from "ai";

// ------------------------------------------------------------------------------
// TAVILY SEARCH TOOL
// ------------------------------------------------------------------------------

export interface TavilySearchResult {
  title: string;
  url: string;
  content: string;
  relevance_score?: number;
}

const searchInputSchema = z.object({
  query: z.string().min(1).describe("The search query to search the web for."),
  searchDepth: z.enum(["basic", "advanced"]).default("basic").describe("The depth of the search. Use advanced for more thorough research."),
});

/**
 * Common Tavily search implementation
 */
async function callTavilyApi(query: string, searchDepth: "basic" | "advanced" = "basic"): Promise<TavilySearchResult[]> {
  const apiKey = process.env.TAVILY_API_KEY;
  if (!apiKey || apiKey === "tu_clave_tavily_aqui") {
    throw new Error("TAVILY_API_KEY is not configured or is using the placeholder.");
  }

  console.log(`[TavilySearch] Query: "${query}", Depth: ${searchDepth}`);

  const response = await fetch("https://api.tavily.com/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      api_key: apiKey,
      query: query,
      search_depth: searchDepth,
      include_answer: false,
      include_images: false,
      max_results: 8,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Tavily API request failed: ${response.status}`);
  }

  const data = await response.json();
  return (data.results || []).map((r: any) => ({
    title: r.title,
    url: r.url,
    content: r.content,
    relevance_score: r.score,
  }));
}

export const tavilySearchTool = tool({
  description: "Search the web for real-time information, news, and research using Tavily. Always cite sources using [Title](URL) format.",
  inputSchema: searchInputSchema,
  execute: async ({ query, searchDepth }) => {
    try {
      const results = await callTavilyApi(query, searchDepth);
      return {
        success: true,
        query,
        results,
      };
    } catch (error: any) {
      console.error("[TavilySearchTool] Error:", error.message);
      return {
        success: false,
        query,
        results: [],
        error: error.message,
      };
    }
  },
});

// Alias for compatibility if needed
export const valyuDeepSearchTool = tavilySearchTool;
export const valyuWebSearchTool = tavilySearchTool;
