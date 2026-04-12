import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

// ============================================
// Users Table
// ============================================
export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  fullName: text("full_name"),
  avatarUrl: text("avatar_url"),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),

  // Valyu OAuth metadata
  valyuSub: text("valyu_sub"),
  valyuUserType: text("valyu_user_type"),
  valyuOrganisationId: text("valyu_organisation_id"),
  valyuOrganisationName: text("valyu_organisation_name"),

  // Subscription info
  subscriptionTier: text("subscription_tier").default("valyu"),
  subscriptionStatus: text("subscription_status").default("active"),
});

// ============================================
// Analysis Sessions Table
// ============================================
export const analysisSessions = sqliteTable("analysis_sessions", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),

  // Market identification
  marketUrl: text("market_url").notNull(),
  platform: text("platform").default("polymarket"),
  marketIdentifier: text("market_identifier").notNull(),
  marketQuestion: text("market_question"),

  // Legacy column
  polymarketSlug: text("polymarket_slug"),

  // Status tracking
  status: text("status").default("pending"),
  startedAt: integer("started_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  currentStep: text("current_step"),
  progressEvents: text("progress_events"), // JSON string

  // Analysis results
  forecastResult: text("forecast_result"), // JSON string
  forecastCard: text("forecast_card"), // JSON string
  analysisSteps: text("analysis_steps"), // JSON string
  fullResponse: text("full_response"),
  markdownReport: text("markdown_report"),

  // Metadata
  p0: real("p0"),
  pNeutral: real("p_neutral"),
  pAware: real("p_aware"),
  drivers: text("drivers"), // JSON string
  durationSeconds: integer("duration_seconds"),
  valyuCost: real("valyu_cost").default(0),
  errorMessage: text("error_message"),

  // Timestamps
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  completedAt: integer("completed_at", { mode: "timestamp" }),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

// ============================================
// Featured Markets Table
// ============================================
export const featuredMarkets = sqliteTable("featured_markets", {
  id: integer("id").primaryKey({ autoIncrement: true }),

  // Market identification
  slug: text("slug").notNull(),
  question: text("question").notNull(),
  category: text("category"),

  // Platform-specific URLs
  polymarketUrl: text("polymarket_url").notNull(),
  marketUrl: text("market_url"),
  platform: text("platform").default("polymarket"),

  // Market metadata
  volume: integer("volume").notNull().default(0),
  endDate: integer("end_date", { mode: "timestamp" }).notNull(),
  currentOdds: text("current_odds"), // JSON string

  // Display configuration
  sortOrder: integer("sort_order").notNull().default(0),
  isActive: integer("is_active", { mode: "boolean" }).notNull().default(true),

  // Timestamps
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" })
    .notNull()
    .default(sql`(unixepoch())`),
});

// ============================================
// Type Exports
// ============================================
export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type AnalysisSession = typeof analysisSessions.$inferSelect;
export type InsertAnalysisSession = typeof analysisSessions.$inferInsert;
export type FeaturedMarket = typeof featuredMarkets.$inferSelect;
export type InsertFeaturedMarket = typeof featuredMarkets.$inferInsert;
