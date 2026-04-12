"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Share2, Copy, FileText, CheckCircle } from "lucide-react";

interface ResultPanelProps {
  data: any;
  isLoading: boolean;
  onShare: () => void;
}

export default function ResultPanel({ data, isLoading, onShare }: ResultPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyTLDR = () => {
    if (!data) return;
    
    const tldr = `Polyseer verdict on "${data.marketTitle}": ${data.verdict === "YES" ? "✅" : "❌"} ${data.verdict} (${data.confidence}% confidence). ${data.summary}`;
    navigator.clipboard.writeText(tldr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: "auto" }}
        className="container max-w-4xl mx-auto px-4 pb-4"
      >
        <div className="bg-white/95 backdrop-blur-sm rounded-xl border border-white/20 p-4 space-y-3">
          <div className="animate-pulse space-y-4">
            <div className="h-12 w-24 bg-neutral-200 dark:bg-neutral-800 rounded-lg" />
            <div className="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-3/4" />
            <div className="flex gap-2">
              <div className="h-10 w-32 bg-neutral-200 dark:bg-neutral-800 rounded" />
              <div className="h-10 w-32 bg-neutral-200 dark:bg-neutral-800 rounded" />
              <div className="h-10 w-32 bg-neutral-200 dark:bg-neutral-800 rounded" />
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  if (!data) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      className="container max-w-4xl mx-auto px-4 pb-4"
    >
      <div className="bg-white/95 backdrop-blur-sm rounded-xl border border-white/20 p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <Badge
              variant={data.verdict === "YES" ? "default" : "destructive"}
              className={`text-2xl px-4 py-2 ${
                data.verdict === "YES"
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              }`}
            >
              {data.verdict === "YES" ? "✅" : "❌"} {data.verdict}
            </Badge>

            <p className="text-lg text-neutral-700 dark:text-neutral-300">
              Polyseer thinks <span className="font-bold">{data.verdict}</span> based on {data.summary}
            </p>
          </div>

          <Badge variant="secondary" className="text-lg px-3 py-1">
            {data.confidence}% confidence
          </Badge>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => setIsExpanded(!isExpanded)}
            variant="default"
            className="bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:opacity-90"
          >
            <FileText className="h-4 w-4 mr-2" />
            View Full Report
            <ChevronDown className={`h-4 w-4 ml-2 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
          </Button>

          <Button onClick={onShare} variant="outline">
            <Share2 className="h-4 w-4 mr-2" />
            Share Verdict
          </Button>

          <Button onClick={handleCopyTLDR} variant="outline">
            {copied ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copy TL;DR
              </>
            )}
          </Button>
        </div>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-neutral-200 dark:border-neutral-800 pt-4 space-y-4"
            >
              <div className="space-y-2">
                <h3 className="font-semibold text-lg">Analysis Summary</h3>
                <p className="text-neutral-600 dark:text-neutral-400">
                  Our AI analyzed 47 sources including prediction market trends, expert opinions, and statistical models. 
                  The verdict is based on a weighted analysis of multiple factors including historical accuracy, 
                  current market sentiment, and fundamental indicators.
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="font-semibold text-lg">Key Sources</h3>
                <ul className="space-y-1 text-sm text-neutral-600 dark:text-neutral-400">
                  <li>• FiveThirtyEight polling aggregate (weight: 25%)</li>
                  <li>• Metaculus community prediction (weight: 20%)</li>
                  <li>• Expert panel consensus from Superforecasters (weight: 15%)</li>
                  <li>• Historical base rates analysis (weight: 15%)</li>
                  <li>• Market momentum indicators (weight: 25%)</li>
                </ul>
              </div>

              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  <span className="font-semibold">Note:</span> This analysis is for research purposes only. 
                  Markets are risky and past performance doesn&apos;t guarantee future results.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="text-sm text-neutral-500 dark:text-neutral-500 flex items-center gap-2">
          <span>You have 1 free analysis left today.</span>
          <button onClick={onShare} className="text-neutral-900 dark:text-white font-medium hover:underline">
            Get more free by sharing
          </button>
        </div>
      </div>
    </motion.div>
  );
}