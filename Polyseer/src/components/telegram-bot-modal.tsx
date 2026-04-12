"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { MessageCircle, Bell, TrendingUp } from "lucide-react";

interface TelegramBotModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function TelegramBotModal({ open, onOpenChange }: TelegramBotModalProps) {
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  const handleOpenTelegram = () => {
    window.open("https://t.me/PolyseerBot", "_blank");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl">Add Polyseer Bot</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="text-center space-y-4">
            <div className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <MessageCircle className="h-10 w-10 text-white" />
            </div>

            <p className="text-lg font-medium">
              Daily AI pick at 9am + instant pings when odds move or our verdict flips
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex items-start gap-3 text-sm">
              <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
              <div>
                <p className="font-medium">Daily Top Pick</p>
                <p className="text-neutral-600 dark:text-neutral-400">
                  Get our highest confidence bet every morning at 9am
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 text-sm">
              <Bell className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
              <div>
                <p className="font-medium">Real-time Alerts</p>
                <p className="text-neutral-600 dark:text-neutral-400">
                  Instant notification when verdicts flip or odds shift significantly
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
            <label htmlFor="alerts" className="text-sm font-medium cursor-pointer">
              Send alerts for markets I follow
            </label>
            <button
              id="alerts"
              onClick={() => setAlertsEnabled(!alertsEnabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                alertsEnabled ? "bg-blue-600" : "bg-neutral-300 dark:bg-neutral-700"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  alertsEnabled ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          <Button onClick={handleOpenTelegram} className="w-full bg-[#0088cc] hover:bg-[#0077bb] text-white">
            <MessageCircle className="h-4 w-4 mr-2" />
            Open in Telegram
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}