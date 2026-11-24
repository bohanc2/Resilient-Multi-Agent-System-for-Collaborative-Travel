"use client";

import React from "react";
import { X, Clock, DollarSign, Footprints, MapPin, Tag, Sun, CloudRain } from "lucide-react";
import { VenueInfo } from "../types";

interface VenueDetailDrawerProps {
  venue: VenueInfo | null;
  onClose: () => void;
}

export default function VenueDetailDrawer({ venue, onClose }: VenueDetailDrawerProps) {
  if (!venue) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-[2px] animate-in fade-in duration-150">
      <div className="w-full max-w-sm h-full bg-white border-l border-gray-200 p-6 flex flex-col justify-between shadow-xl animate-in slide-in-from-right duration-200">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-gray-100">
            <div>
              <span className="text-[11px] font-mono font-semibold uppercase text-gray-400 block mb-1">
                Venue Details
              </span>
              <h3 className="text-lg font-bold text-gray-900 tracking-tight">
                {venue.name}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Key Attributes Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 block flex items-center gap-1">
                <DollarSign className="w-3.5 h-3.5 text-gray-600" /> Cost / Person
              </span>
              <span className="text-sm font-bold text-gray-900">
                NT$ {venue.cost}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 block flex items-center gap-1">
                <Footprints className="w-3.5 h-3.5 text-gray-600" /> Walk Effort
              </span>
              <span className="text-sm font-bold text-gray-900">
                Lv. {venue.walk}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 block flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-gray-600" /> Hours
              </span>
              <span className="text-xs font-semibold text-gray-800">
                {venue.open} - {venue.close}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-1">
              <span className="text-gray-400 block flex items-center gap-1">
                {venue.indoor ? <Sun className="w-3.5 h-3.5 text-sky-600" /> : <CloudRain className="w-3.5 h-3.5 text-emerald-600" />}
                Environment
              </span>
              <span className="text-xs font-semibold text-gray-800">
                {venue.indoor ? "Indoor Venue" : "Outdoor Venue"}
              </span>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
              Overview
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-xl border border-gray-100">
              {venue.description || "Curated point of interest selected based on group profile matching."}
            </p>
          </div>

          {/* Tags */}
          {venue.tags && venue.tags.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                Category Tags
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {venue.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 text-[11px] font-medium"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-100 text-right">
          <button
            onClick={onClose}
            className="w-full py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold transition-colors"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
}
