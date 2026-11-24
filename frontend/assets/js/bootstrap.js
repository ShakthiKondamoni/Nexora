(async () => {
  try {
    const a = await api("/api/auth/status");
    if (a.owner_exists && !a.authenticated) {
      location.replace("/signin?expired=1");
      return;
    }
  } catch (e) {
    console.warn("authentication status unavailable", e);
  }
  try {
    await loadCfg();
  } catch (e) {
    console.warn("settings unavailable", e);
  }
  await Promise.all([loadChats(), loadModels()]);
  arm();
  poll();
  const cb = new URLSearchParams(location.search);
  if (cb.has("github_connected") || cb.has("github_error"))
    await setView("connected-apps");
  else if (
    ["general", "connected-apps", "appearance"].includes(cb.get("settings"))
  )
    await setView(cb.get("settings"));
  else go("chat");
})();
