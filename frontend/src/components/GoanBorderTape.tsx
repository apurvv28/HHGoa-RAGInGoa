import React from "react";

interface GoanBorderTapeProps {
  className?: string;
}

export const GoanBorderTape: React.FC<GoanBorderTapeProps> = ({ className = "" }) => {
  return (
    <div className={`w-full overflow-hidden bg-[#FFE500] py-2 border-y-2 border-[#044425] flex items-center justify-between shadow-md ${className}`}>
      <div className="flex items-center space-x-6 min-w-full justify-around select-none">
        {Array.from({ length: 16 }).map((_, i) => (
          <div key={i} className="flex items-center space-x-3 shrink-0">
            {/* Geometric Flower/Star Motif */}
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="#075E34" />
              <circle cx="12" cy="12" r="3" fill="#FF1D78" />
              <path d="M5 5L8 8M19 5L16 8M19 19L16 16M5 19L8 16" stroke="#075E34" strokeWidth="2" />
            </svg>
            <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[10px] border-b-[#FF1D78]" />
            <circle cx="4" cy="4" r="3" className="fill-[#075E34]" />
          </div>
        ))}
      </div>
    </div>
  );
};
