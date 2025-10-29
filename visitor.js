// Visitor Tracker - Frontend Snippet
// Add this to your GitHub.io page (in <head> or before </body>)

(async function() {
  try {
    // Collect visitor information
    const visitorData = {
      timestamp: new Date().toISOString(),
      page: window.location.pathname,
      referrer: document.referrer || 'direct',
      userAgent: navigator.userAgent,
      language: navigator.language,
      screenResolution: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    };

    // Send to your tracking endpoint
    // Replace with your actual worker/serverless URL
    const TRACKING_ENDPOINT = 'https://your-worker.your-subdomain.workers.dev/track';
    
    await fetch(TRACKING_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(visitorData),
      // Don't wait for response, fire and forget
      keepalive: true
    }).catch(() => {
      // Silently fail - don't interrupt user experience
    });
  } catch (error) {
    // Silently fail - tracking shouldn't break the page
  }
})();
