import React from "react";

interface HeaderProps {
  onStartClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onStartClick }) => {
  return (
    <header className="w-full px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between z-30 select-none">
      {/* 2:47 PM STUDIO Logo */}
      <div className="flex items-center cursor-pointer group" onClick={onStartClick}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/2-47.svg"
          alt="2:47 PM STUDIO"
          className="h-8 sm:h-10 md:h-12 w-auto object-contain drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)] group-hover:scale-105 transition-transform"
        />
      </div>

      {/* Navigation & Credits */}
      <div className="flex items-center space-x-4 md:space-x-8">
        <a
          href="#"
          onClick={(e) => e.preventDefault()}
          className="flex flex-col items-end group cursor-pointer text-right transition-transform hover:scale-105"
        >
          <span className="font-mono text-[10px] sm:text-xs font-bold text-[#FFE500]/80 tracking-wider uppercase">
            Developed By:
          </span>
          <span className="font-mono text-xs sm:text-sm font-black text-[#FFE500] group-hover:text-[#FF1D78] tracking-widest uppercase transition-colors drop-shadow-[0_1px_2px_rgba(0,0,0,0.6)]">
            Team TechTadkaa
          </span>
        </a>
      </div>
    </header>
  );
};
