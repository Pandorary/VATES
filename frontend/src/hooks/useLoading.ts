import { useState, useCallback } from "react";

export const useLoading = () => {
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");

  const startLoading = useCallback((message: string = "加载中...") => {
    setLoadingMessage(message);
    setLoading(true);
  }, []);

  const stopLoading = useCallback(() => {
    setLoading(false);
    setLoadingMessage("");
  }, []);

  return {
    loading,
    loadingMessage,
    startLoading,
    stopLoading,
  };
};
