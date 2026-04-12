"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Search, Brain, CheckCircle2 } from "lucide-react";

interface HowItWorksModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function HowItWorksModal({ open, onOpenChange }: HowItWorksModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-xl">How Polyseer Works</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                <Search className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold mb-1">1. Crawl sources via Valyu DeepSearch</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  We analyze 40+ sources including prediction markets, expert opinions, polling data, 
                  and statistical models. Every source is cited and weighted.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold mb-1">2. Synthesize with OpenAI into analyst brief</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  Our AI model processes all data points, identifies patterns, and generates 
                  a comprehensive analysis similar to professional research reports.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h3 className="font-semibold mb-1">3. Output Yes/No verdict + confidence + sources</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  Get a clear verdict with confidence percentage, key reasoning, and all sources 
                  used in the analysis. Full transparency in seconds.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <span className="font-semibold">Important:</span> Not financial advice. For research only. 
              Markets are risky and predictions can be wrong. Always do your own research.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}