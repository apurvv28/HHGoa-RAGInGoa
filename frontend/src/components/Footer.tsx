import React from "react";
import { HeroLogo } from "./HeroLogo";
import { Send, Mail } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-[#075E34] border-t-4 border-[#FFE500] relative overflow-hidden select-none py-8 sm:py-10 px-4 sm:px-6">
      {/* Background Banner Image with 0.6 Opacity */}
      <div className="absolute inset-0 bg-[url('/banner1.jpeg')] bg-cover bg-center bg-no-repeat opacity-60 pointer-events-none" />

      <div className="max-w-6xl mx-auto relative z-10 flex flex-col items-center">
        {/* Footer Hero Logo */}
        <HeroLogo size="xs" className="py-1" />

        {/* Footer Links & Info Container */}
        <div className="w-full max-w-3xl mx-auto flex flex-col md:flex-row items-center md:items-start justify-center gap-8 md:gap-16 my-4 sm:my-6 font-mono text-xs md:text-sm text-[#FFE500] border-y border-[#FFE500]/30 py-6">
          {/* Social Contacts */}
          <div className="space-y-3 flex flex-col items-center md:items-start text-center md:text-left w-full md:w-auto">
            <a
              href="https://x.com/247PMSTUDIO"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-3 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5 text-[#FF1D78] fill-current shrink-0" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              <span className="font-bold">@247PMSTUDIO</span>
            </a>

            <a
              href="https://t.me/twofourtysevenpm"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-3 hover:text-white transition-colors"
            >
              <Send className="w-5 h-5 text-[#FFE500] shrink-0" />
              <span className="font-bold">@TWOFOURTYSEVENPM</span>
            </a>

            <a
              href="mailto:satapathyprayasu@gmail.com"
              className="flex items-center space-x-3 hover:text-white transition-colors max-w-full"
            >
              <Mail className="w-5 h-5 text-[#FF1D78] shrink-0" />
              <span className="font-bold text-[11px] sm:text-xs md:text-sm break-all">SATAPATHYPRAYASU@GMAIL.COM</span>
            </a>
          </div>

          {/* Additional Links & Copyright */}
          <div className="flex flex-col justify-between items-center md:items-start space-y-4 text-center md:text-left w-full md:w-auto">
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 sm:gap-6 font-bold">
              <a href="#" className="hover:text-white transition-colors">BRAND KIT</a>
              <span>•</span>
              <a href="#" className="hover:text-white transition-colors">TERMS &amp; CONDITIONS</a>
            </div>

            <p className="text-[#FFE500]/90 font-bold text-center md:text-left text-xs">
              © 2026 HH-GOA. ALL RIGHTS RESERVED.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};
