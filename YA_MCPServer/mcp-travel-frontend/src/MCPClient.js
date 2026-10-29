// src/MCPClient.js
export class MCPClient {
  constructor(baseUrl = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
    this.eventSource = null;
    this.pendingRequests = new Map();
  }

  async initialize() {
    // 1. 获取 session_id
    const res = await fetch(`${this.baseUrl}/`);
    const text = await res.text();
    const url = new URL(text.trim(), this.baseUrl);
    this.sessionId = url.searchParams.get('session_id');
    
    if (!this.sessionId) {
      throw new Error("Failed to get session_id from server");
    }
    console.log("✅ Session initialized:", this.sessionId);

    // 2. 建立 SSE 监听连接
    this.eventSource = new EventSource(`${this.baseUrl}/?session_id=${this.sessionId}`);
    
    this.eventSource.onmessage = (event) => this.handleSseMessage(event);
    this.eventSource.addEventListener('message', (event) => this.handleSseMessage(event));
    this.eventSource.addEventListener('result', (event) => this.handleSseMessage(event));

    this.eventSource.onerror = (err) => {
      console.error("SSE connection error:", err);
    };

    // 3. 发送初始化通知
    await this.sendInitializedNotification();
  }

  // 发送初始化通知
  async sendInitializedNotification() {
    const response = await fetch(
      `${this.baseUrl}/messages?session_id=${this.sessionId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "notifications/initialized"
        })
      }
    );

    if (!response.ok) {
      throw new Error(`Initialization failed: ${response.status} ${response.statusText}`);
    }
    console.log("✅ Sent initialized notification");
  }

  handleSseMessage(event) {
    try {
      if (event.data.startsWith(':')) return; // 忽略 ping
      
      const data = JSON.parse(event.data);
      
      // 处理 JSON-RPC 响应
      if (data.jsonrpc === "2.0" && typeof data.id !== 'undefined') {
        const request = this.pendingRequests.get(data.id);
        if (request) {
          if (data.error) {
            request.reject(new Error(`Tool error: ${JSON.stringify(data.error)}`));
          } else {
            request.resolve(data);
          }
          this.pendingRequests.delete(data.id);
        }
      }
    } catch (e) {
      console.debug("Non-JSON SSE message:", event.data);
    }
  }

  async callTool(name, args) {
    return this.call({
      method: "call_tool",
      params: { name, arguments: args }
    });
  }

  async call(request) {
    if (!this.sessionId) {
      throw new Error("MCPClient not initialized. Call initialize() first.");
    }

    const requestId = Date.now();
    const promise = new Promise((resolve, reject) => {
      this.pendingRequests.set(requestId, { resolve, reject });
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId);
          reject(new Error("Request timeout"));
        }
      }, 30000);
    });

    const postResponse = await fetch(
      `${this.baseUrl}/messages?session_id=${this.sessionId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: requestId,
          ...request
        })
      }
    );

    if (!postResponse.ok) {
      throw new Error(`POST failed: ${postResponse.status} ${postResponse.statusText}`);
    }

    return promise;
  }

  close() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.pendingRequests.clear();
  }
}