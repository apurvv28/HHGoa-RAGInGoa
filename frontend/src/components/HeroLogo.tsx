import React from "react";

interface HeroLogoProps {
  className?: string;
  size?: "xs" | "sm" | "md" | "lg";
}

export const HeroLogo: React.FC<HeroLogoProps> = ({ className = "", size = "lg" }) => {
  const isLg = size === "lg";
  const isMd = size === "md";
  const isXs = size === "xs";

  const logoMaxHeight = isLg
    ? "max-h-42 sm:max-h-52 md:max-h-64"
    : isMd
    ? "max-h-24 sm:max-h-32"
    : isXs
    ? "max-h-10 sm:max-h-14"
    : "max-h-16 sm:max-h-20";

  const hindiWidth = isLg
    ? "w-20 sm:w-28 md:w-36"
    : isMd
    ? "w-16 sm:w-24"
    : isXs
    ? "w-10 sm:w-16"
    : "w-12 sm:w-20";

  return (
    <div className={`relative flex flex-col items-center justify-center text-center select-none ${isXs ? "py-2" : "py-6"} ${className}`}>
      {/* Title Container with Official Assets */}
      <div className="relative inline-flex items-center justify-center max-w-4xl w-full px-4">
        {/* HACKER HOUSE Official PNG Graphic */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/Hacker house.png"
          alt="HACKER HOUSE"
          className={`w-full h-auto object-contain drop-shadow-[0_8px_16px_rgba(0,0,0,0.6)] ${logoMaxHeight}`}
        />

        {/* Superimposed Official Devanagari "गोवा" SVG Badge */}
        <div className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none transform -rotate-3 ${hindiWidth}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/goa_hindi.svg"
            alt="गोवा"
            className="w-full h-auto drop-shadow-[0_6px_14px_rgba(0,0,0,0.8)]"
          />
        </div>
      </div>

      {/* Date & Location Tagline */}
      <div className={`${isXs ? "mt-3 text-[10px]" : "mt-6 md:mt-8 text-xs sm:text-sm md:text-base"} flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4 text-[#FFE500] font-mono tracking-widest uppercase`}>
        <span className="bg-[#044425]/90 px-3 py-1 border border-[#FFE500]/40 rounded-sm">
          GOA, INDIA
        </span>
        <span className="hidden sm:inline text-[#FF1D78] font-bold">•</span>
        <span className="bg-[#044425]/90 px-3 py-1 border border-[#FFE500]/40 rounded-sm">
          28 – 31 OCT 2026
        </span>
        <span className="hidden sm:inline text-[#FF1D78] font-bold">•</span>
        <span className="text-[#FF1D78] font-bold">2:47 PM STUDIO</span>
      </div>
    </div>
  );
};
