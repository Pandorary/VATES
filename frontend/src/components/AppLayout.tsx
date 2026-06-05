import { Outlet, NavLink } from "react-router-dom";
import { Toaster } from "sonner";

const navItems = [
  { to: "/", label: "首页" },
  { to: "/prediction-track", label: "预测跟踪" },
  { to: "/watchlist", label: "持仓诊断" },
  { to: "/prompts", label: "提示词管理" },
];

const AppLayout = () => {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="w-full border-b border-gray-200 h-14 flex items-center px-6 gap-10">
        <div className="flex flex-col items-center">
          <div className="text-base font-semibold text-black leading-tight">VATES</div>
          <span className="text-[10px] text-gray-400 leading-tight">see the future</span>
        </div>
        <nav className="flex gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded-md transition-colors ${
                  isActive
                    ? "text-primary bg-primary/10 font-medium"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
};

export default AppLayout;
