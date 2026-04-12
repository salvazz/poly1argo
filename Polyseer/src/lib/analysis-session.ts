import {
  createAnalysisSession as dbCreateSession,
  updateAnalysisSession as dbUpdateSession,
  getAnalysisHistory as dbGetHistory,
  getAnalysisById as dbGetById,
  Platform,
} from "./db";

export type { Platform };

export interface AnalysisSession {
  id: string;
  userId: string;
  marketUrl: string;
  platform: Platform;
  marketIdentifier: string;
  marketQuestion?: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  startedAt: Date;
  completedAt?: Date;
  analysisSteps?: any;
  markdownReport?: string;
  forecastCard?: any;
  currentStep?: string;
  progressEvents?: any[];
  durationSeconds?: number;
  p0?: number;
  pNeutral?: number;
  pAware?: number;
  drivers?: any;
  valyuCost?: number;
  errorMessage?: string;
}

// Helper to detect platform from URL
function detectPlatform(url: string): Platform {
  if (!url) return "unknown";
  if (url.includes("polymarket.com")) return "polymarket";
  if (url.includes("kalshi.com")) return "kalshi";
  return "unknown";
}

// Helper to extract identifier from URL
function extractIdentifier(url: string, platform: Platform): string {
  if (!url) return "";

  try {
    const urlObj = new URL(url);

    if (platform === "polymarket") {
      // https://polymarket.com/event/slug or https://polymarket.com/event/slug/submarket
      const pathParts = urlObj.pathname.split("/").filter(Boolean);
      if (pathParts[0] === "event" && pathParts[1]) {
        return pathParts[1];
      }
    }

    if (platform === "kalshi") {
      // https://kalshi.com/markets/series/category/ticker
      const pathParts = urlObj.pathname.split("/").filter(Boolean);
      if (pathParts[0] === "markets" && pathParts.length >= 2) {
        return pathParts.slice(1).join("/");
      }
    }

    return url;
  } catch {
    return url;
  }
}

export async function createAnalysisSession(
  userId: string,
  marketUrl: string
): Promise<AnalysisSession> {
  const platform = detectPlatform(marketUrl);
  const marketIdentifier = extractIdentifier(marketUrl, platform);

  const { data, error } = await dbCreateSession(
    userId,
    marketUrl,
    platform,
    marketIdentifier
  );

  if (error || !data) {
    console.error("Failed to create analysis session:", error);
    throw new Error("Failed to create analysis session");
  }

  return {
    id: data.id,
    userId,
    marketUrl,
    platform,
    marketIdentifier,
    status: "pending",
    startedAt: new Date(),
  };
}

export async function updateAnalysisSession(
  sessionId: string,
  updates: Partial<AnalysisSession>
) {
  const { error } = await dbUpdateSession(sessionId, updates);

  if (error) {
    console.error("Failed to update analysis session:", error);
    throw new Error("Failed to update analysis session");
  }
}

export async function completeAnalysisSession(
  sessionId: string,
  markdownReport: string,
  analysisSteps: any,
  forecastCard?: any,
  additionalData?: {
    marketQuestion?: string;
    p0?: number;
    pNeutral?: number;
    pAware?: number;
    drivers?: any;
    valyuCost?: number;
    durationSeconds?: number;
  }
) {
  const updates: Partial<AnalysisSession> = {
    status: "completed",
    completedAt: new Date(),
    markdownReport,
    analysisSteps,
    forecastCard,
  };

  if (additionalData) {
    if (additionalData.marketQuestion)
      updates.marketQuestion = additionalData.marketQuestion;
    if (additionalData.p0 !== undefined) updates.p0 = additionalData.p0;
    if (additionalData.pNeutral !== undefined)
      updates.pNeutral = additionalData.pNeutral;
    if (additionalData.pAware !== undefined)
      updates.pAware = additionalData.pAware;
    if (additionalData.drivers) updates.drivers = additionalData.drivers;
    if (additionalData.valyuCost !== undefined)
      updates.valyuCost = additionalData.valyuCost;
    if (additionalData.durationSeconds !== undefined)
      updates.durationSeconds = additionalData.durationSeconds;
  }

  await updateAnalysisSession(sessionId, updates);
}

export async function failAnalysisSession(sessionId: string, error: string) {
  await dbUpdateSession(sessionId, {
    status: "failed",
    completedAt: new Date(),
    errorMessage: error,
  });
}

export async function getAnalysisHistory(userId: string) {
  const { data, error } = await dbGetHistory(userId);

  if (error) {
    console.error("Failed to fetch analysis history:", error);
    throw new Error("Failed to fetch analysis history");
  }

  return data;
}

export async function getAnalysisById(analysisId: string, userId: string) {
  const { data, error } = await dbGetById(analysisId, userId);

  if (error) {
    console.error("Failed to fetch analysis:", error);
    throw new Error("Failed to fetch analysis");
  }

  return data;
}
