"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { MapPin, CalendarDays, Users, ArrowRight, Menu, X } from "lucide-react";

/* ─────────────────────────────────────────────
   SVG Logo mark
───────────────────────────────────────────── */
function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" stroke="white" strokeWidth="1.5" strokeOpacity="0.6" />
      <path
        d="M24 8 L28 20 H40 L30 28 L34 40 L24 32 L14 40 L18 28 L8 20 H20 Z"
        fill="white"
        fillOpacity="0.85"
      />
    </svg>
  );
}

/* ─────────────────────────────────────────────
   Grain overlay (pure CSS, no image needed)
───────────────────────────────────────────── */
function Grain() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 opacity-[0.035]"
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        backgroundRepeat: "repeat",
        backgroundSize: "128px 128px",
      }}
    />
  );
}

/* ─────────────────────────────────────────────
   Sticky "Plan My Trip" nav bar
───────────────────────────────────────────── */
function PlanNav({ visible }: { visible: boolean }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <AnimatePresence>
      {visible && (
        <motion.header
          key="plan-nav"
          initial={{ y: -80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -80, opacity: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-x-0 top-0 z-50"
        >
          {/* Frosted bar */}
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mt-3 rounded-2xl border border-white/10 bg-black/60 px-4 py-3 shadow-2xl backdrop-blur-xl sm:px-6">
              {/* Desktop */}
              <div className="flex items-center justify-between gap-4">
                {/* Logo */}
                <a href="/" className="flex items-center gap-2 shrink-0">
                  <LogoMark className="h-7 w-7" />
                  <span className="hidden text-sm font-semibold tracking-wide text-white/90 sm:block">
                    VOYA
                  </span>
                </a>

                {/* Fields — hidden on mobile */}
                <div className="hidden md:flex items-center gap-1 flex-1 justify-center">
                  <NavField icon={<MapPin className="h-3.5 w-3.5" />} label="Destination" placeholder="Where to?" />
                  <Divider />
                  <NavField icon={<CalendarDays className="h-3.5 w-3.5" />} label="Dates" placeholder="Add dates" />
                  <Divider />
                  <NavField icon={<Users className="h-3.5 w-3.5" />} label="Travelers" placeholder="Add guests" />
                </div>

                {/* CTA + mobile toggle */}
                <div className="flex items-center gap-2 shrink-0">
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.97 }}
                    className="flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-black shadow-lg transition-colors hover:bg-white/90"
                  >
                    Plan My Trip
                    <ArrowRight className="h-3.5 w-3.5" />
                  </motion.button>
                  <button
                    onClick={() => setMobileOpen((v) => !v)}
                    className="flex md:hidden items-center justify-center rounded-lg p-2 text-white/70 hover:bg-white/10"
                  >
                    {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              {/* Mobile dropdown */}
              <AnimatePresence>
                {mobileOpen && (
                  <motion.div
                    key="mobile-menu"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.28, ease: "easeInOut" }}
                    className="overflow-hidden md:hidden"
                  >
                    <div className="mt-3 flex flex-col gap-2 border-t border-white/10 pt-3">
                      <MobileField icon={<MapPin className="h-4 w-4" />} label="Destination" placeholder="Where to?" />
                      <MobileField icon={<CalendarDays className="h-4 w-4" />} label="Dates" placeholder="Add dates" />
                      <MobileField icon={<Users className="h-4 w-4" />} label="Travelers" placeholder="Add guests" />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.header>
      )}
    </AnimatePresence>
  );
}

function Divider() {
  return <div className="h-6 w-px bg-white/15 shrink-0" />;
}

function NavField({
  icon,
  label,
  placeholder,
}: {
  icon: React.ReactNode;
  label: string;
  placeholder: string;
}) {
  return (
    <button className="group flex items-center gap-2 rounded-xl px-3 py-2 text-left transition-colors hover:bg-white/8">
      <span className="text-white/40 group-hover:text-white/70 transition-colors">{icon}</span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-white/40">{label}</p>
        <p className="text-xs font-medium text-white/70">{placeholder}</p>
      </div>
    </button>
  );
}

function MobileField({
  icon,
  label,
  placeholder,
}: {
  icon: React.ReactNode;
  label: string;
  placeholder: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/5 px-4 py-3">
      <span className="text-white/40">{icon}</span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-white/40">{label}</p>
        <p className="text-sm text-white/60">{placeholder}</p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Main Hero
───────────────────────────────────────────── */
export default function TravelHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [navVisible, setNavVisible] = useState(false);

  const { scrollY } = useScroll();

  // Logo: fades out + moves up on scroll
  const logoOpacity = useTransform(scrollY, [0, 180], [1, 0]);
  const logoY = useTransform(scrollY, [0, 180], [0, -40]);

  // Title: fades out + moves down on scroll
  const titleOpacity = useTransform(scrollY, [0, 180], [1, 0]);
  const titleY = useTransform(scrollY, [0, 180], [0, 40]);

  useEffect(() => {
    const unsub = scrollY.on("change", (v) => setNavVisible(v > 60));
    return unsub;
  }, [scrollY]);

  return (
    <>
      <Grain />
      <PlanNav visible={navVisible} />

      {/* Hero screen */}
      <div
        ref={containerRef}
        className="relative flex h-screen w-full flex-col items-center justify-between overflow-hidden bg-[#080810]"
      >
        {/* Ambient gradient */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-0"
          style={{
            background:
              "radial-gradient(ellipse 70% 50% at 50% 20%, rgba(99,102,241,0.14) 0%, transparent 70%), " +
              "radial-gradient(ellipse 60% 40% at 80% 80%, rgba(168,85,247,0.10) 0%, transparent 65%)",
          }}
        />

        {/* ── Logo (top) ── */}
        <motion.div
          style={{ opacity: logoOpacity, y: logoY }}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          className="relative z-10 flex flex-col items-center gap-3 pt-14 sm:pt-20"
        >
          <LogoMark className="h-14 w-14 sm:h-16 sm:w-16 drop-shadow-[0_0_24px_rgba(255,255,255,0.18)]" />
          <span className="text-[11px] font-semibold tracking-[0.35em] text-white/50 uppercase">
            VOYA
          </span>
        </motion.div>

        {/* ── Title (bottom) ── */}
        <motion.div
          style={{ opacity: titleOpacity, y: titleY }}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1], delay: 0.45 }}
          className="relative z-10 w-full px-6 pb-16 sm:pb-20 text-center"
        >
          {/* Eyebrow */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7, duration: 0.8 }}
            className="mb-4 text-xs font-semibold uppercase tracking-[0.3em] text-white/35"
          >
            Luxury Travel · Curated Experiences
          </motion.p>

          {/* Main headline */}
          <h1 className="font-serif text-[clamp(2.6rem,8vw,6rem)] font-light leading-[1.05] tracking-[-0.025em] text-white">
            The World{" "}
            <span
              style={{
                background: "linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 40%, #c084fc 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Awaits
            </span>
          </h1>

          {/* Subtext */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.8 }}
            className="mx-auto mt-4 max-w-md text-[15px] font-light leading-relaxed text-white/40"
          >
            Bespoke journeys crafted by AI. Scroll to begin planning your perfect escape.
          </motion.p>

          {/* Scroll cue */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.4, duration: 0.8 }}
            className="mt-10 flex justify-center"
          >
            <ScrollCue />
          </motion.div>
        </motion.div>
      </div>

      {/* Content below hero — gives enough scroll room */}
      <div className="relative z-10 min-h-screen bg-[#080810]" />
    </>
  );
}

/* Animated scroll cue */
function ScrollCue() {
  return (
    <div className="flex flex-col items-center gap-2">
      <span className="text-[10px] uppercase tracking-[0.25em] text-white/25">Scroll</span>
      <div className="relative h-9 w-5 rounded-full border border-white/20">
        <motion.div
          animate={{ y: [2, 14, 2] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute left-1/2 top-1.5 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-white/50"
        />
      </div>
    </div>
  );
}
