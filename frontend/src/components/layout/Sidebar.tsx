"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, FileText, Search, BarChart3,
  Activity, LogOut, ChevronRight,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { logout } from "@/lib/auth";
import { useRouter } from "next/navigation";

const NAV_ITEMS = [
  { label: "Dashboard",  href: "/dashboard",           icon: LayoutDashboard },
  { label: "Reports",    href: "/dashboard/reports",   icon: FileText },
  { label: "Search",     href: "/dashboard/search",    icon: Search },
  { label: "Analytics",  href: "/dashboard/analytics", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    clearAuth();
    router.push("/login");
  };

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-60 flex flex-col z-30"
      style={{
        backgroundColor: "var(--sidebar-bg)",
        borderRight: "1px solid var(--sidebar-border)",
      }}
    >
      {/* Logo */}
      <div
        className="h-16 flex items-center px-5 gap-3"
        style={{ borderBottom: "1px solid var(--sidebar-border)" }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: "var(--sidebar-logo-bg)" }}
        >
          <Activity size={15} style={{ color: "var(--sidebar-logo-icon)" }} />
        </div>
        <div>
          <span
            className="text-sm font-bold tracking-wide"
            style={{ color: "var(--sidebar-text-primary)" }}
          >
            RadSight
          </span>
          <span
            className="block text-[10px] font-mono"
            style={{ color: "var(--sidebar-text-muted)" }}
          >
            v1.0 · AI Platform
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p
          className="text-[10px] uppercase tracking-widest px-3 mb-2"
          style={{ color: "var(--sidebar-text-muted)" }}
        >
          Navigation
        </p>
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn("sidebar-item", active && "active")}
            >
              <Icon size={15} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={11} style={{ opacity: 0.5 }} />}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div
        className="px-3 py-4 space-y-0.5"
        style={{ borderTop: "1px solid var(--sidebar-border)" }}
      >
        <div className="flex items-center gap-3 px-3 py-2 mb-1">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{
              backgroundColor: "var(--sidebar-avatar-bg)",
              color: "var(--sidebar-avatar-text)",
            }}
          >
            {user?.full_name?.[0] ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p
              className="text-xs font-medium truncate"
              style={{ color: "var(--sidebar-text-primary)" }}
            >
              {user?.full_name ?? "User"}
            </p>
            <p
              className="text-[10px] capitalize"
              style={{ color: "var(--sidebar-text-muted)" }}
            >
              {user?.role ?? "—"}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="sidebar-item w-full hover:!text-rose-400 hover:!bg-rose-400/10"
        >
          <LogOut size={14} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
