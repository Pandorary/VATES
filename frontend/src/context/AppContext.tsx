import React, { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface AppState {
  disclaimerAccepted: boolean;
}

interface AppContextType {
  state: AppState;
  updateState: (updates: Partial<AppState>) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AppState>({
    disclaimerAccepted: false,
  });

  // 从 localStorage 加载状态
  useEffect(() => {
    const savedState = localStorage.getItem("app-state");
    if (savedState) {
      setState(JSON.parse(savedState));
    }
  }, []);

  // 状态变化时保存到 localStorage
  useEffect(() => {
    localStorage.setItem("app-state", JSON.stringify(state));
  }, [state]);

  const updateState = (updates: Partial<AppState>) => {
    setState((prevState) => ({ ...prevState, ...updates }));
  };

  return <AppContext.Provider value={{ state, updateState }}>{children}</AppContext.Provider>;
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
