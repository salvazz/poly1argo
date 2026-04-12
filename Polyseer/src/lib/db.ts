/**
 * Unified database interface that switches between Supabase (valyu mode)
 * and SQLite (self-hosted mode) based on NEXT_PUBLIC_APP_MODE
 */

import { createClient as createSupabaseClient } from "@/utils/supabase/server";
import { getLocalDb, DEV_USER_ID } from "./local-db/client";
import { getDevUser, isSelfHostedMode } from "./local-db/local-auth";
import { eq, desc, and } from "drizzle-orm";
import * as schema from "./local-db/schema";
import { v4 as uuidv4 } from "uuid";

// ============================================================================
// AUTH FUNCTIONS
// ============================================================================

export async function getUser() {
  if (isSelfHostedMode()) {
    return { data: { user: getDevUser() }, error: null };
  }

  const supabase = await createSupabaseClient();
  return await supabase.auth.getUser();
}

export async function getSession() {
  if (isSelfHostedMode()) {
    return {
      data: {
        session: {
          user: getDevUser(),
          access_token: "dev-access-token",
        },
      },
      error: null,
    };
  }

  const supabase = await createSupabaseClient();
  return await supabase.auth.getSession();
}

// ============================================================================
// USER FUNCTIONS
// ============================================================================

export async function getUserById(userId: string) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const user = await db.query.users.findFirst({
      where: eq(schema.users.id, userId),
    });
    return { data: user || null, error: null };
  }

  const supabase = await createSupabaseClient();
  const { data, error } = await supabase
    .from("users")
    .select("*")
    .eq("id", userId)
    .single();
  return { data, error };
}

export async function upsertUser(userData: {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  valyu_sub?: string;
  valyu_user_type?: string;
  valyu_organisation_id?: string;
  valyu_organisation_name?: string;
}) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const existing = await db.query.users.findFirst({
      where: eq(schema.users.id, userData.id),
    });

    if (existing) {
      await db
        .update(schema.users)
        .set({
          email: userData.email,
          fullName: userData.full_name,
          avatarUrl: userData.avatar_url,
          valyuSub: userData.valyu_sub,
          valyuUserType: userData.valyu_user_type,
          valyuOrganisationId: userData.valyu_organisation_id,
          valyuOrganisationName: userData.valyu_organisation_name,
          updatedAt: new Date(),
        })
        .where(eq(schema.users.id, userData.id));
    } else {
      await db.insert(schema.users).values({
        id: userData.id,
        email: userData.email,
        fullName: userData.full_name,
        avatarUrl: userData.avatar_url,
        valyuSub: userData.valyu_sub,
        valyuUserType: userData.valyu_user_type,
        valyuOrganisationId: userData.valyu_organisation_id,
        valyuOrganisationName: userData.valyu_organisation_name,
      });
    }

    return { error: null };
  }

  const supabase = await createSupabaseClient();
  const { error } = await supabase.from("users").upsert(userData);
  return { error };
}

// ============================================================================
// ANALYSIS SESSION FUNCTIONS
// ============================================================================

export type Platform = "polymarket" | "kalshi" | "unknown";

export interface AnalysisSessionData {
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

export async function createAnalysisSession(
  userId: string,
  marketUrl: string,
  platform: Platform,
  marketIdentifier: string
): Promise<{ data: { id: string } | null; error: any }> {
  const sessionId = uuidv4();

  if (isSelfHostedMode()) {
    const db = getLocalDb();
    await db.insert(schema.analysisSessions).values({
      id: sessionId,
      userId,
      marketUrl,
      platform,
      marketIdentifier,
      polymarketSlug: platform === "polymarket" ? marketIdentifier : null,
      status: "pending",
      startedAt: new Date(),
    });
    return { data: { id: sessionId }, error: null };
  }

  const supabase = await createSupabaseClient();
  const { error } = await supabase.from("analysis_sessions").insert({
    id: sessionId,
    user_id: userId,
    market_url: marketUrl,
    platform,
    market_identifier: marketIdentifier,
    polymarket_slug: platform === "polymarket" ? marketIdentifier : null,
    status: "pending",
    started_at: new Date().toISOString(),
  });

  if (error) {
    return { data: null, error };
  }

  return { data: { id: sessionId }, error: null };
}

export async function updateAnalysisSession(
  sessionId: string,
  updates: Partial<AnalysisSessionData>
) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const dbUpdates: Partial<schema.InsertAnalysisSession> = {
      updatedAt: new Date(),
    };

    if (updates.status !== undefined) dbUpdates.status = updates.status;
    if (updates.completedAt !== undefined) dbUpdates.completedAt = updates.completedAt;
    if (updates.analysisSteps !== undefined)
      dbUpdates.analysisSteps = JSON.stringify(updates.analysisSteps);
    if (updates.markdownReport !== undefined) dbUpdates.markdownReport = updates.markdownReport;
    if (updates.forecastCard !== undefined)
      dbUpdates.forecastCard = JSON.stringify(updates.forecastCard);
    if (updates.currentStep !== undefined) dbUpdates.currentStep = updates.currentStep;
    if (updates.progressEvents !== undefined)
      dbUpdates.progressEvents = JSON.stringify(updates.progressEvents);
    if (updates.durationSeconds !== undefined) dbUpdates.durationSeconds = updates.durationSeconds;
    if (updates.p0 !== undefined) dbUpdates.p0 = updates.p0;
    if (updates.pNeutral !== undefined) dbUpdates.pNeutral = updates.pNeutral;
    if (updates.pAware !== undefined) dbUpdates.pAware = updates.pAware;
    if (updates.drivers !== undefined) dbUpdates.drivers = JSON.stringify(updates.drivers);
    if (updates.marketQuestion !== undefined) dbUpdates.marketQuestion = updates.marketQuestion;
    if (updates.valyuCost !== undefined) dbUpdates.valyuCost = updates.valyuCost;
    if (updates.errorMessage !== undefined) dbUpdates.errorMessage = updates.errorMessage;

    await db
      .update(schema.analysisSessions)
      .set(dbUpdates)
      .where(eq(schema.analysisSessions.id, sessionId));

    return { error: null };
  }

  const supabase = await createSupabaseClient();
  const dbUpdates: any = {};

  if (updates.status !== undefined) dbUpdates.status = updates.status;
  if (updates.completedAt !== undefined)
    dbUpdates.completed_at = updates.completedAt.toISOString();
  if (updates.analysisSteps !== undefined) dbUpdates.analysis_steps = updates.analysisSteps;
  if (updates.markdownReport !== undefined) dbUpdates.markdown_report = updates.markdownReport;
  if (updates.forecastCard !== undefined) dbUpdates.forecast_card = updates.forecastCard;
  if (updates.currentStep !== undefined) dbUpdates.current_step = updates.currentStep;
  if (updates.progressEvents !== undefined) dbUpdates.progress_events = updates.progressEvents;
  if (updates.durationSeconds !== undefined) dbUpdates.duration_seconds = updates.durationSeconds;
  if (updates.p0 !== undefined) dbUpdates.p0 = updates.p0;
  if (updates.pNeutral !== undefined) dbUpdates.p_neutral = updates.pNeutral;
  if (updates.pAware !== undefined) dbUpdates.p_aware = updates.pAware;
  if (updates.drivers !== undefined) dbUpdates.drivers = updates.drivers;
  if (updates.marketQuestion !== undefined) dbUpdates.market_question = updates.marketQuestion;
  if (updates.valyuCost !== undefined) dbUpdates.valyu_cost = updates.valyuCost;
  if (updates.errorMessage !== undefined) dbUpdates.error_message = updates.errorMessage;

  const { error } = await supabase
    .from("analysis_sessions")
    .update(dbUpdates)
    .eq("id", sessionId);

  return { error };
}

export async function getAnalysisHistory(userId: string) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const sessions = await db.query.analysisSessions.findMany({
      where: and(
        eq(schema.analysisSessions.userId, userId),
        eq(schema.analysisSessions.status, "completed")
      ),
      orderBy: [desc(schema.analysisSessions.completedAt)],
      limit: 20,
    });

    // Transform to match Supabase format
    return {
      data: sessions.map((s) => ({
        id: s.id,
        market_url: s.marketUrl,
        market_question: s.marketQuestion,
        platform: s.platform,
        market_identifier: s.marketIdentifier,
        status: s.status,
        p0: s.p0,
        p_neutral: s.pNeutral,
        p_aware: s.pAware,
        valyu_cost: s.valyuCost,
        started_at: s.startedAt?.toISOString(),
        completed_at: s.completedAt?.toISOString(),
        duration_seconds: s.durationSeconds,
        forecast_card: s.forecastCard ? JSON.parse(s.forecastCard) : null,
      })),
      error: null,
    };
  }

  const supabase = await createSupabaseClient();
  const { data, error } = await supabase
    .from("analysis_sessions")
    .select(
      `
      id,
      market_url,
      market_question,
      platform,
      market_identifier,
      status,
      p0,
      p_neutral,
      p_aware,
      valyu_cost,
      started_at,
      completed_at,
      duration_seconds,
      forecast_card
    `
    )
    .eq("user_id", userId)
    .eq("status", "completed")
    .order("completed_at", { ascending: false })
    .limit(20);

  return { data, error };
}

export async function getAnalysisById(analysisId: string, userId: string) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const session = await db.query.analysisSessions.findFirst({
      where: and(
        eq(schema.analysisSessions.id, analysisId),
        eq(schema.analysisSessions.userId, userId)
      ),
    });

    if (!session) {
      return { data: null, error: { message: "Not found" } };
    }

    // Transform to match Supabase format
    return {
      data: {
        id: session.id,
        user_id: session.userId,
        market_url: session.marketUrl,
        market_question: session.marketQuestion,
        platform: session.platform,
        market_identifier: session.marketIdentifier,
        polymarket_slug: session.polymarketSlug,
        status: session.status,
        started_at: session.startedAt?.toISOString(),
        completed_at: session.completedAt?.toISOString(),
        current_step: session.currentStep,
        progress_events: session.progressEvents ? JSON.parse(session.progressEvents) : null,
        forecast_result: session.forecastResult ? JSON.parse(session.forecastResult) : null,
        forecast_card: session.forecastCard ? JSON.parse(session.forecastCard) : null,
        analysis_steps: session.analysisSteps ? JSON.parse(session.analysisSteps) : null,
        markdown_report: session.markdownReport,
        p0: session.p0,
        p_neutral: session.pNeutral,
        p_aware: session.pAware,
        drivers: session.drivers ? JSON.parse(session.drivers) : null,
        duration_seconds: session.durationSeconds,
        valyu_cost: session.valyuCost,
        error_message: session.errorMessage,
        created_at: session.createdAt?.toISOString(),
        updated_at: session.updatedAt?.toISOString(),
      },
      error: null,
    };
  }

  const supabase = await createSupabaseClient();
  const { data, error } = await supabase
    .from("analysis_sessions")
    .select("*")
    .eq("id", analysisId)
    .eq("user_id", userId)
    .single();

  return { data, error };
}

export async function deleteAnalysisSession(analysisId: string, userId: string) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    await db
      .delete(schema.analysisSessions)
      .where(
        and(
          eq(schema.analysisSessions.id, analysisId),
          eq(schema.analysisSessions.userId, userId)
        )
      );
    return { error: null };
  }

  const supabase = await createSupabaseClient();
  const { error } = await supabase
    .from("analysis_sessions")
    .delete()
    .eq("id", analysisId)
    .eq("user_id", userId);

  return { error };
}

// ============================================================================
// FEATURED MARKETS FUNCTIONS
// ============================================================================

export async function getFeaturedMarkets() {
  if (isSelfHostedMode()) {
    const db = getLocalDb();
    const markets = await db.query.featuredMarkets.findMany({
      where: eq(schema.featuredMarkets.isActive, true),
      orderBy: [desc(schema.featuredMarkets.volume)],
      limit: 4,
    });

    // Transform to match Supabase format
    return {
      data: markets.map((m) => ({
        id: m.id,
        slug: m.slug,
        question: m.question,
        category: m.category,
        polymarket_url: m.polymarketUrl,
        market_url: m.marketUrl,
        platform: m.platform,
        volume: m.volume,
        end_date: m.endDate?.toISOString(),
        current_odds: m.currentOdds ? JSON.parse(m.currentOdds) : null,
        sort_order: m.sortOrder,
        is_active: m.isActive,
      })),
      error: null,
    };
  }

  const supabase = await createSupabaseClient();
  const { data, error } = await supabase
    .from("featured_markets")
    .select("*")
    .eq("is_active", true)
    .order("sort_order", { ascending: true })
    .order("volume", { ascending: false })
    .limit(4);

  return { data, error };
}

export async function updateFeaturedMarkets(
  markets: Array<{
    slug: string;
    question: string;
    polymarket_url: string;
    market_url: string;
    volume: number;
    end_date: string;
    current_odds: any;
    sort_order: number;
    platform: string;
    is_active: boolean;
  }>
) {
  if (isSelfHostedMode()) {
    const db = getLocalDb();

    // Delete all existing featured markets
    await db.delete(schema.featuredMarkets);

    // Insert new markets
    if (markets.length > 0) {
      await db.insert(schema.featuredMarkets).values(
        markets.map((m) => ({
          slug: m.slug,
          question: m.question,
          polymarketUrl: m.polymarket_url,
          marketUrl: m.market_url,
          volume: m.volume,
          endDate: new Date(m.end_date),
          currentOdds: JSON.stringify(m.current_odds),
          sortOrder: m.sort_order,
          platform: m.platform,
          isActive: m.is_active,
        }))
      );
    }

    return { error: null };
  }

  const supabase = await createSupabaseClient();

  // Delete all existing
  await supabase.from("featured_markets").delete().neq("id", 0);

  // Insert new
  if (markets.length > 0) {
    const { error } = await supabase.from("featured_markets").insert(markets);
    return { error };
  }

  return { error: null };
}

// ============================================================================
// DEV MODE HELPERS
// ============================================================================

export { isSelfHostedMode, DEV_USER_ID };
